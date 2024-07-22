from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from typing import Literal

class NRAO_archive_downloader:

	def __init__(self):

		self.email = 'ddong@nrao.edu'
		self.default_request_description = 'doordash order for kale to feed my rabbits'
		self.timeout = 20 # How long to keep retrying function calls before timing out (seconds)
		self.retry_interval = 0.1 # How often to keep retrying function calls (seconds)
		self.boxes = {}
		self.buttons = {}

		if self.email is None:
			email = input('Please enter your email for the download submission form here: ')
			setattr(self, 'email', email)

		# Initialize the Chrome driver and connect to data.nrao.edu
		self.setup_driver() 

		# Click the show search inputs button
		self.retry(self.click_button, text = '▼ Show Search Inputs ▼') 

		# Find all of the search boxes on the search page
		self.retry(self.get_boxes) 

	def setup_driver(self):
		try:
			print('Initializing NRAO downloader')
			service = Service(ChromeDriverManager().install())
			self.driver = webdriver.Chrome(service=service)

			print('Opening NRAO archive')
			self.driver.get("https://data.nrao.edu/portal/#/")
		except Exception as e:
			if self.driver:
				self.driver.quit()
			raise Exception('Error in setting up driver!') from e
	
	def get_buttons(self, print_text = False):
		'''Gets all of the buttons on the current page'''

		self.buttons = {}

		buttons = self.driver.find_elements(By.TAG_NAME, "button")
		for i, button in enumerate(buttons):
			attributes = self.list_attributes(button)
			self.buttons[f'button_{i}'] = attributes
			self.buttons[f'button_{i}']['object'] = button

			if print_text:
				print(f'Attributes of button {i}: {attributes}\n')
		

		return buttons

	def retry(self, func, **kwargs):
		start_time = time.time()
		kwargs_str = ', '.join(f'{key}={value}' for key, value in kwargs.items())
		print(f'Attempting to call function {func.__name__} with kwargs {kwargs_str}')
		while time.time() - start_time < self.timeout:
			try:
				func(**kwargs)
				print(f'Time elapsed: {(time.time()-start_time):.2f} seconds')
				return True
			except:
				time.sleep(self.retry_interval)

		raise Exception(f'Function {func.__name__} timed out after {self.timeout} seconds')


	def retry_click_object(self, obj):
		start_time = time.time()
		print(f'Attempting to click object {obj}')
		while time.time() - start_time < self.timeout:
			try:
				obj.click()
				print(f'Success! Time elapsed: {(time.time()-start_time):.2f} seconds')
				return True
			except:
				time.sleep(self.retry_interval)

		raise Exception(f'Timed out after {self.timeout} seconds')



	def click_button(self, text = None, attribute = None, val = None):
		# Find all button elements
		buttons = self.get_buttons()

		if text is not None:
			# Loop through buttons to find the one with the desired text
			for button in buttons:
				if button.text == text:
					button.click()
					print(f'Successfully clicked button with text {text}')
					return

		elif attribute is not None:
			for button in buttons:
				if button.get_attribute(attribute) == val:
					button.click()
					print(f'Successfully clicked button with {attribute = }, {val = }')
					return

		raise Exception


	def get_boxes(self):
		'''Gets all of the input boxes on the current page'''
		boxes = self.driver.find_elements(By.XPATH, "//input[not(@type) or @type!='hidden']")

		self.reset_boxes()
		
		for i, box in enumerate(boxes):
			try:
				attributes = self.list_attributes(box)
				self.boxes[f'box_{i}'] = attributes
				self.boxes[f'box_{i}']['object'] = box

			except Exception as e:
				print(f"Error accessing input box: {e}")

		return boxes
		

	def search_subdicts(self, attr, val, dictionary):
		for key, sub_dict in dictionary.items():
			if sub_dict.get(attr) == val:
				return key, sub_dict
		return None, None

	def input_text(self, inputs: dict, verbose = False):

		for name, text in inputs.items():
			try:
				box_number, box_attrs = self.search_subdicts(attr = 'name', val = name, dictionary = self.boxes)
				input_id = box_attrs['id']
				if verbose:
					print(f'Attempting to enter {text = } in box with {name = }, {input_id = }')
				box = self.driver.find_element(By.ID, input_id)
				box.clear()
				box.send_keys(text)
				print(f'Entered text "{text}" into input box with name "{name}"')

			except Exception as e:
				print(e)
				raise Exception


	def list_attributes(self, button):
		'''Lists all attributes of a button'''
		attributes = self.driver.execute_script('''
			var items = {}; 
			for (index = 0; index < arguments[0].attributes.length; ++index) {
				items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value
			}; 
			return items;
		''', button)
		return attributes

	def search(self, search_inputs: dict = None, **kwargs):
		'''When on the search page, use this function to search for your observation'''
		if search_inputs == None:
			search_inputs = kwargs
		self.retry(self.input_text, inputs = search_inputs)
		self.retry(self.click_button, text = 'Search')

	def click_row_toggle(self, project_code):
		row_toggle = f'row-toggle-for-{project_code}'
		self.retry(self.click_button, attribute = 'id', val = row_toggle)

	def download(self, create_tar = True, download_format: None = Literal['SDMonly','SDM','MS','CMS'], submit_request = False):
		'''Launch the download once you've clicked the row toggle'''

		# Select the ms for download
		self.retry(self.click_button, attribute = 'uib-tooltip', val = 'Select for download')

		# Open the download form
		self.retry(self.click_button, attribute = 'ng-click', val = '$ctrl.openDownloadForm($ctrl.selectedObj)')
	
		# Create the download request
		_ = self.retry(self.get_boxes)

		download_inputs = {
		'emailNotification': self.email, 
		'requestDescription': self.default_request_description
		}
		self.retry(self.input_text, inputs = download_inputs)

		if create_tar:
			_, box = self.search_subdicts(attr = 'name', val= 'p_createTarFile', dictionary = self.boxes)
			tar_click_box = box['object']
			self.retry_click_object(tar_click_box)
	
		if download_format != 'CMS':
			download_format_str = f'workflow-event-launcher-form-observation-processing-operation-process-evla-observation-p-downloadDataFormat-{download_format}'
			_, box = self.search_subdicts(attr = 'id', val = download_format_str, dictionary = self.boxes)
			download_format_object = box['object']
			self.retry_click_object(download_format_object)

		if submit_request:
			buttons = self.get_buttons()
			_, button = self.search_subdicts(attr = 'id', val = 'submit-workflow-request-button', dictionary = self.buttons)
			submit_button = button['object']
			self.retry_click_object(submit_button)


	def reset_boxes(self):
		self.boxes = {}
		print('Reset self.boxes to {}')


	def set_element_value(self, element, value):
		self.driver.execute_script("arguments[0].value = arguments[1];", element, value)


	def quit(self):
		if self.driver:
			self.driver.quit()

# Example: downloading a SB with known project code and obs_id:

if __name__ == '__main__':
	project_code = '16A-197'
	obs_id = 'sb31830391.eb31893393.57446.070232847225'

	dl = NRAO_archive_downloader()
	_ = dl.search(project_code = project_code, obs_id = obs_id)
	_ = dl.click_row_toggle(project_code)
	_ = dl.download(download_format = 'SDMonly', create_tar = True, submit_request = True)


'''
buttons = dl.get_buttons()
for i, button in enumerate(buttons):
	attributes = dl.list_attributes(button)
	print(f'Attributes of button {i}: {attributes}\n')

boxes = dl.get_boxes()
for i, button in enumerate(boxes):
	attributes = dl.list_attributes(button)
	print(f'Attributes of button {i}: {attributes}\n')
'''


