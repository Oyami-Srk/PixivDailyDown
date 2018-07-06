# -*- coding: utf-8 -*-
# -*- audhot: shiroko -*-
# -*- date: 18/07/04 -*-
# Description: Download daily images and manage the db

from pixivpy3 import *
import yaml
import os
import logging
import time
import re
from ImgDownloader import Downloader
from retrying import retry


def print_dict(dict):
    import json
    print(json.dumps(dict, ensure_ascii=False, indent=1))


pixiv_api = AppPixivAPI()
config = {}
logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger('log')

try:
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.load(f)
except Exception as e:
    logger.fatal('Cannot read config.yaml!')
    import sys
    sys.exit()

print_dict(config)

try:
    pixiv_config = config['dailypixiv_config']['pixiv']
    assert 'username' in pixiv_config.keys()
    assert 'password' in pixiv_config.keys()
except AssertionError as e:
    logger.error('Config has no username or password(or both) to login!')
    import sys
    sys.exit()

try:
    download_config = config['dailypixiv_config']['download']
    assert 'work_path' in download_config.keys()
except AssertionError as e:
    logger.error('Config has no need download config!')
    import sys
    sys.exit()

try:
    if not os.path.exists(
            os.path.join(os.getcwd(), download_config['work_path'])):
        os.makedirs(os.path.join(os.getcwd(), download_config['work_path']))
    os.chdir(os.path.join(os.getcwd(), download_config['work_path']))
except Exception as e:
    logger.fetal('Cannot cd to work path!')
    import sys
    sys.exit()


def get_newest_downloaded_id():
    dirs = os.listdir(os.getcwd())
    # sorted(l, key = lambda i:int(re.findall('\d+',i).pop()))
    dirs.sort()
    """
    daily_dir = dirs.pop()
    today_dir = time.strftime('D%y%m%d', time.localtime())
    print('Today\'s dir is ' + today_dir)
    while not daily_dir[0] == 'D' or not os.path.isdir(daily_dir):
        daily_dir = dirs.pop()
    if today_dir == daily_dir:
        # daily_dir = dirs.pop()
        pass
    """

    @retry
    def get_id(dir_list):
        daily_dir = dir_list.pop()
        img_files = []
        for root, dirs, files in os.walk(daily_dir):
            for file in files:
                img_files.append(file)

        def get_pid(fn):
            r = re.findall(r'(\d{8,10})_p', fn)
            return int(r.pop()) if len(r) > 0 else 0

        img_files = list(map(get_pid, img_files))
        img_files.sort()
        return img_files.pop()

    return get_id(dirs)


def get_updated_illust_id(api, id=0):
    ids = []
    max_id = 600
    page = api.illust_follow()
    target_id = id or get_newest_downloaded_id()
    finded = False
    while len(ids) < max_id and not finded:
        ids_page = list(
            map(lambda n: page.illusts[n].id, range(0, len(page.illusts))))
        if target_id in ids_page:
            ids_page = ids_page[:ids_page.index(target_id)]
            finded = True
        else:
            page = api.illust_follow(**api.parse_qs(page.next_url))
        ids = ids + ids_page
    return ids


def pixiv_download(api, illust_id, dler, logger):
    img_url = []
    try:
        detail = api.illust_detail(illust_id)
        if detail.illust.page_count == 1:
            img_url.append(detail.illust.meta_single_page.original_image_url)
        else:
            for page in detail.illust.meta_pages:
                img_url.append(page.image_urls.original)
    except Exception as e:
        logger.error('Cannot fetch details of illust_id: ' + str(illust_id))
        return

    try:
        for url in img_url:
            dler.download(url, referer='https://app-api.pixiv.net/')
    except Exception as e:
        logger.error('Error downloading illust: ' + str(illust_id))
        return

    logger.info('Download quene append: ' + str(illust_id))


def pixiv_download_list(api, illust_id_list, target_dir, logger):
    dler = Downloader(logger=logger, base_path=target_dir)
    for illust_id in illust_id_list:
        pixiv_download(api, illust_id, dler, logger)
    logger.info('Waiting for complete.')
    dler.close()
    logger.info('All completed! Total: ' + str(len(illust_id_list)))


if __name__ == '__main__':
    logger.info('Program started')
    pixiv_api.login(pixiv_config['username'], pixiv_config['password'])
    """
    dler = Downloader(logger=logger, base_path='img_test')
    print(get_newest_downloaded_id())
    while True:
        id = input('Pixiv id> ')
        print(': ' + id)
        if id == '0':
            break
        detail = pixiv_api.illust_detail(id)
        print_dict(detail)
        dler.download(
            detail['illust']['meta_single_page']['original_image_url'],
            referer='https://app-api.pixiv.net/')
    """
    today_dir = time.strftime('D%y%m%d', time.localtime())
    pixiv_download_list(pixiv_api, get_updated_illust_id(pixiv_api), today_dir,
                        logger)
