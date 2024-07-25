from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import time
from typing import Literal


class NRAO_archive_downloader:
    def __init__(self):
        self.email = 'ddong@nrao.edu'
        self.default_request_description = 'doordash order for kale to feed my rabbits'
        self.boxes = {}
        self.buttons = {}

        if self.email is None:
            self.email = input('Please enter your email for the download submission form here: ')

        self.setup_driver()
        self.click_button(text='▼ Show Search Inputs ▼')
        self.get_boxes()

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Exception, TimeoutError)))
    def setup_driver(self):
        try:
            print('Initializing NRAO downloader')
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service)
            print('Opening NRAO archive')
            self.driver.get("https://data.nrao.edu/portal/#/")
        except Exception as e:
            if hasattr(self, 'driver'):
                self.driver.quit()
            raise Exception('Error in setting up driver!') from e

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Exception, TimeoutError)))
    def get_elements(self, element_type, container_dict, print_text=False):
        elements = self.driver.find_elements(By.TAG_NAME, element_type)
        for i, element in enumerate(elements):
            attributes = self.list_attributes(element)
            container_dict[f'{element_type}_{i}'] = {**attributes, 'object': element}
            if print_text:
                print(f'Attributes of {element_type} {i}: {attributes}\n')
        return elements

    def get_buttons(self, print_text=False):
        self.buttons = {}
        return self.get_elements("button", self.buttons, print_text)

    def get_boxes(self):
        self.boxes = {}
        return self.get_elements("input", self.boxes)

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Exception, TimeoutError)))
    def click_button(self, text=None, attribute=None, val=None):
        buttons = self.get_buttons()
        for button in buttons:
            if (text and button.text == text) or (attribute and button.get_attribute(attribute) == val):
                button.click()
                print(f'Successfully clicked button with {"text" if text else attribute} {text or val}')
                return
        raise Exception("Button not found")

    def search_subdicts(self, attr, val, dictionary):
        for key, sub_dict in dictionary.items():
            if sub_dict.get(attr) == val:
                return key, sub_dict
        return None, None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Exception, TimeoutError)))
    def input_text(self, inputs: dict, verbose=False):
        for name, text in inputs.items():
            try:
                _, box_attrs = self.search_subdicts(attr='name', val=name, dictionary=self.boxes)
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

    def list_attributes(self, element):
        return self.driver.execute_script('''
            var items = {}; 
            for (index = 0; index < arguments[0].attributes.length; ++index) {
                items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value
            }; 
            return items;
        ''', element)

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Exception, TimeoutError)))
    def search(self, search_inputs: dict = None, **kwargs):
        search_inputs = search_inputs or kwargs
        self.input_text(inputs=search_inputs)
        self.click_button(text='Search')

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Exception, TimeoutError)))
    def click_row_toggle(self, project_code):
        self.click_button(attribute='id', val=f'row-toggle-for-{project_code}')

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Exception, TimeoutError)))
    def download(self, create_tar=True, download_format: Literal['SDMonly', 'SDM', 'MS', 'CMS'] = None, submit_request=False):
        # Select for download
        self.click_button(attribute='uib-tooltip', val='Select for download')
        
        # Open the download form
        self.click_button(attribute='ng-click', val='$ctrl.openDownloadForm($ctrl.selectedObj)')
        
        # Wait for the new form to appear and refresh the boxes
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "emailNotification"))
        )
        self.get_boxes()  # Refresh the boxes after the new form appears

        download_inputs = {
            'emailNotification': self.email,
            'requestDescription': self.default_request_description
        }
        self.input_text(inputs=download_inputs)

        if create_tar:
            tar_checkbox = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "p_createTarFile"))
            )
            if not tar_checkbox.is_selected():
                tar_checkbox.click()

        if download_format and download_format != 'CMS':
            download_format_str = f'workflow-event-launcher-form-observation-processing-operation-process-evla-observation-p-downloadDataFormat-{download_format}'
            format_radio = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, download_format_str))
            )
            format_radio.click()

        if submit_request:
            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "submit-workflow-request-button"))
            )
            submit_button.click()

    def quit(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

if __name__ == '__main__':
    project_code = '16A-197'
    obs_id = 'sb31830391.eb31893393.57446.070232847225'

    dl = NRAO_archive_downloader()
    dl.search(project_code=project_code, obs_id=obs_id)
    dl.click_row_toggle(project_code)
    dl.download(download_format='SDMonly', create_tar=True, submit_request=False)
    #dl.quit()