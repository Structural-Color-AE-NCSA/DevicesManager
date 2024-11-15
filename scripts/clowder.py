import os
import requests
from datetime import timedelta, datetime
import pyclowder.datasets
from requests_toolbelt.multipart.encoder import MultipartEncoder

def upload_a_file_to_dataset(url, filepath):
    # url = '%s/api/uploadToDataset/%s?key=%s&folder_id=%s' % (
    # CLOWDER_URL, dataset_id, CLOWDER_KEY, clowder_upload_folder_id)
    before = datetime.now()
    if os.path.exists(filepath):
            filename = os.path.basename(filepath)
            m = MultipartEncoder(
                fields={'file': (filename, open(filepath, 'rb'))}
            )
            try:
                result = requests.post(url, data=m, headers={'Content-Type': m.content_type},
                                        verify=False)

                uploadedfileid = result.json()
                return uploadedfileid
            except Exception as e:
                print('failed to upload file, error')
                print(e)
                print(str(datetime.now()))
    else:
        print("unable to upload file %s (not found)", filepath)
    return None