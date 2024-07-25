import json
import requests
from dateutil import parser

class NRAOApiClient:
	def __init__(self):
		self.base_url = "https://data.nrao.edu"
		self.session = requests.Session()
		self.session.headers.update({
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
			'Origin': 'https://data.nrao.edu',
			'Accept': 'application/json',
			'Referer': 'https://data.nrao.edu/portal/',
		})

	def _make_request(self, endpoint, method='GET', params=None):
		url = f"{self.base_url}{endpoint}"
		#print(f"DEBUG: Making request to URL: {url}")
		#print(f"DEBUG: with params: {params}")
		response = self.session.request(method, url, params=params)
		response.raise_for_status()
		#print(f"DEBUG: Response status code: {response.status_code}")
		#print(f"DEBUG: Response content type: {response.headers.get('Content-Type')}")
		#print(f"DEBUG: First 500 characters of response: {response.text[:500]}")
		return response.text

	def get_observation_scans(self, exec_id):
	    endpoint = "/archive-service/restapi_product_details_view"
	    params = {"exec_block_id": exec_id}
	    response = self._make_request(endpoint, params=params)
	    try:
	        return json.loads(response)
	    except json.JSONDecodeError:
	        print(f"Error parsing JSON response: {response}")
	        return None

	def search_execution_blocks(self, project_code, rows=1000, start=0):
		endpoint = "/archive-service/restapi_get_paged_exec_blocks"
		params = {
			"coordsys_refFrame": "Equatorial",
			"equinox": "J2000",
			"project_code": f'"{project_code}"',
			"rows": rows,
			"show_cms_only": "false",
			"show_public_only": "false",
			"sort": "obs_stop desc",
			"start": start
		}
		
		results_text = self._make_request(endpoint, params=params)
		
		try:
			results = json.loads(json.loads(results_text))
			#print(f"DEBUG: Successfully parsed JSON. Keys in result: {results.keys()}")
		except json.JSONDecodeError as e:
			print(f"DEBUG: Error decoding JSON: {e}")
			return {"data": [], "response_msg": {"success": False, "message": "Failed to parse JSON response"}}

		return results

	def get_all_execution_blocks(self, project_code):
		results = self.search_execution_blocks(project_code, rows=1000)
		all_ebs = results['eb_list']
		return all_ebs

	def process_eb_results(self, ebs):
	    processed_data = []

	    for eb in ebs:
	        size_gb = eb['access_estsize'] / (1024 ** 3)
	        exec_id = eb.get('cals', [{}])[0].get('exec_id', None)
	        scan_details = {}

	        if exec_id:
	            observation_scans = self.get_observation_scans(exec_id)
	            scan_details = observation_scans.get('details', {}) if observation_scans else {}

	        processed_data.append({
	            'project_code': eb['project_code'],
	            'title': eb.get('title', 'N/A'),
	            'abstract': eb.get('abstract', 'N/A'),
	            'pi': eb.get('pi', 'N/A'),
	            'obs_start': eb.get('obs_start', 'N/A'),
	            'obs_stop': eb.get('obs_stop', 'N/A'),
	            'instrument': eb.get('instrument_name', 'N/A'),
	            'vla_configuration': eb.get('vla_configuration', 'N/A'),
	            'num_scans': eb.get('num_scans', 'N/A'),
	            'exec_id': exec_id,
	            'bands': eb.get('obs_band', []),
	            'obs_id': eb.get('obs_id', 'N/A'),
	            'dataproduct_type': eb.get('dataproduct_type', 'N/A'),
	            'estimated_size_gb': round(size_gb, 2),
	            'scan_details': scan_details
	        })

	    return processed_data

# Usage example

client = NRAOApiClient()
all_ebs = client.get_all_execution_blocks(project_code="16A-197")
processed_ebs = client.process_eb_results(all_ebs)


print(f"Project Code: {processed_ebs[0]['project_code']}")
print('--------------------------------------------------')
print(f"Total Estimated Size: {sum(eb['estimated_size_gb'] for eb in processed_ebs) / 1024:.2f} TB")
print(f"Total execution blocks found: {len(processed_ebs)}")
print("Summary of Execution Blocks:")
print('--------------------------------------------------')

obs_dates = [parser.parse(eb['obs_start']).strftime("%Y-%m-%d") for eb in processed_ebs]
unique_dates = set(obs_dates)
print(f"Observation Dates: {len(unique_dates)} unique dates between {min(unique_dates)} and {max(unique_dates)}")


print(f"Average Scans per EB: {sum(eb['num_scans'] for eb in processed_ebs)/len(processed_ebs)}")
obs_dates = [parser.parse(eb['obs_start']).strftime("%Y-%m-%d") for eb in processed_ebs]

target_intents = {}
scan_details_missing = 0
for eb in processed_ebs:
    if 'scan_details' in eb and eb['scan_details']:
        for scan in eb['scan_details']['execution_blocks'][0]['scan_rows']:
            target = scan['target_name']
            intent = scan['intent']
            if target not in target_intents:
                target_intents[target] = {}
            if intent in target_intents[target]:
                target_intents[target][intent] += 1
            else:
                target_intents[target][intent] = 1
    else:
        scan_details_missing += 1

print(f"Number of EBs where scan_details is missing: {scan_details_missing}")

print('--------------------------------------------------')


print("Scan Intents by Target:")
for target, intents in target_intents.items():
    print(f"\nTarget: {target}")
    for intent, count in intents.items():
        print(f"  {intent}: {count}")


'''
client = NRAOApiClient()

print("Searching for all execution blocks by project code:")
all_ebs = client.get_all_execution_blocks(project_code="16A-197")
processed_ebs = client.process_eb_results(all_ebs)

print(f"Total execution blocks found: {len(processed_ebs)}")
for i, eb in enumerate(processed_ebs, 1):
	print(f"\nExecution Block {i}:")
	print(f"Project: {eb['project_code']}")
	print(f"Observation ID: {eb['obs_id']}")
	print(f"Title: {eb['title']}")
	print(f"PI: {eb['pi']}")
	print(f"Estimated Size: {eb['estimated_size_gb']} GB")
'''