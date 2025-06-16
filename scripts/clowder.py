import os
import json
import argparse
import requests
import traceback
from datetime import timedelta, datetime
import pyclowder.datasets
from requests_toolbelt.multipart.encoder import MultipartEncoder

# radiant vm
# CLOWDER_URL = 'http://141.142.219.4:8000'
# CLOWDER_KEY = '2c51012a-c936-4691-aeca-ca29dcaf2869'
# SPACE_ID = '67315595e4b0eea51509dcc7'


# localhost
CLOWDER_URL = 'http://localhost:8000'
CLOWDER_KEY = '610e9be0-aa23-402f-95b4-a0de54ccb76e'
SPACE_ID = '67aa4fbbe4b019057bb4aaa1'


client = pyclowder.datasets.ClowderClient(host=CLOWDER_URL, key=CLOWDER_KEY)


def upload_a_file_to_dataset(filepath, dataset_id, clowder_upload_folder_id, campaign_id, cell_id, number_prints_trigger_prediction = 1, rank_run = 0, accum_h_mu=0.0):
    url = '%s/api/uploadToDataset/%s?key=%s&folder_id=%s' % (
    CLOWDER_URL, dataset_id, CLOWDER_KEY, clowder_upload_folder_id)
    if os.path.exists(filepath):
            filename = os.path.basename(filepath)
            m = MultipartEncoder(
                fields={'file': (filename, open(filepath, 'rb'))}
            )
            try:
                result = requests.post(url, data=m, headers={'Content-Type': m.content_type},
                                        verify=False)

                uploaded_fileid = result.json()

                metadata = dict()
                metadata['image_analysis'] = 'true'
                metadata['campaign_id'] = campaign_id
                metadata['cell_id'] = cell_id
                metadata['number_prints_trigger_prediction'] = number_prints_trigger_prediction
                metadata['rank_run'] = rank_run
                metadata['accum_h_mu'] = accum_h_mu
                try:
                    client.post('/files/' + uploaded_fileid['id'] + '/metadata', content=metadata)
                except Exception as e:
                    print(e)


                return uploaded_fileid
            except Exception as e:
                print('failed to upload file, error')
                print(e)
                print(str(datetime.now()))
    else:
        print("unable to upload file %s (not found)", filepath)
    return None

def get_or_create_folders(dataset_id, folder_name):
    url = '%s/api/datasets/%s/folders?key=%s' % (CLOWDER_URL, dataset_id, CLOWDER_KEY)
    r = requests.get(url, headers={"Content-type": "application/json",
               "accept": "application/json"}, verify=False)
    folder_id = None
    if r.status_code == 200:
        folders = json.loads(r.content.decode('utf-8'))
        for folder in folders:
            if folder.get('name') == '/'+folder_name:
                folder_id = folder.get('id')

    if folder_id is None:
        url = '%s/api/datasets/%s/newFolder?key=%s' % (CLOWDER_URL, dataset_id, CLOWDER_KEY)
        try:
            result = requests.post(url, data=json.dumps({"name": folder_name, "parentId": dataset_id, "parentType": "dataset"}),
                                   headers={'Content-type': 'application/json', 'accept': 'application/json'},
                                   verify=False)
            csv_folder_id = result.json().get('id')
        except :
            traceback.print_exc()

    return folder_id


def get_or_create_dataset(dataset_name):
    dataset_name = dataset_name.replace("-", "_")

    search_dataset = client.get('/search', params={'query': dataset_name, 'resource_type': 'dataset'})

    if search_dataset['results']:
        return search_dataset['results'][0]['id']
    else:
        data = dict()
        now = datetime.now()
        data["name"] = dataset_name
        data["description"] = f"Created at {now}"
        data["space"] = [SPACE_ID]
        data["collection"] = []
        result = client.post("/datasets/createempty", content=data, params=data)
        return result['id']

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="demo color updates")
    parser.add_argument("-d", "--dataset_name", required=True, help="dataset name")
    parser.add_argument("-f", "--folder_name", required=True, help="folder name")
    parser.add_argument("-p", "--campaign_id", required=True, help="campaign id")
    parser.add_argument("-c", "--cell_id", required=True, help="cell id")
    parser.add_argument("-a", "--accum_h_mu", required=True, help="accum_h_mu")
    parser.add_argument("-n", "--number_prints_trigger_prediction", required=True,
                             help="number_prints_trigger_prediction")
    parser.add_argument("-r", "--rank_run", required=True, help="rank_run")

    args = parser.parse_args()


    dataset_id = get_or_create_dataset(args.dataset_name)
    folder_id = get_or_create_folders(dataset_id, args.folder_name)
    campaign_id = args.campaign_id
    cell_id = args.cell_id

    number_prints_trigger_prediction = args.number_prints_trigger_prediction
    rank_run = args.rank_run
    accum_h_mu = args.accum_h_mu

    upload_a_file_to_dataset('Green_Sanghyun.jpg', dataset_id, folder_id, campaign_id, cell_id, number_prints_trigger_prediction, rank_run, accum_h_mu)