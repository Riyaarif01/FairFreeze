"""Download publisher-linked IBM synthetic sources outside version control."""
import argparse,urllib.request
from pathlib import Path
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=['HI','LI','both'],default='both');p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent/'external_data');a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    for name in (['HI','LI'] if a.variant=='both' else [a.variant]):
        filename=name+'-Small_Trans.csv';dest=a.directory/filename
        if dest.exists():print('Already exists:',dest);continue
        url='https://www.kaggle.com/api/v1/datasets/download/ealtman2019/ibm-transactions-for-anti-money-laundering-aml/'+filename
        temp=dest.with_suffix('.download')
        try:
            urllib.request.urlretrieve(url,temp);temp.replace(dest);print('Downloaded',dest)
        finally:temp.unlink(missing_ok=True)
