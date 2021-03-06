#!/usr/bin/env python
# encoding: utf-8

# @author: Zhipeng Ye
# @contact: Zhipeng.ye19@xjtlu.edu.cn
# @file: __main__.py
# @time: 2019-11-19 21:01
# @desc: reptile urls from Baidu

import os
import traceback
from os.path import isfile, join
from tkinter import _flatten

import chardet
import requests
from bs4 import BeautifulSoup
from requests import ReadTimeout

import clean_data as cd
import http_tools


def generate_request_baidu_url(file_path):
    file_keyword = open(file_path)
    try:
        file_content = file_keyword.read()
        keywords = file_content.splitlines()
    finally:
        file_keyword.close()
    urls = []
    for keyword in keywords:
        # it seem that baidu is ok
        url = "https://www.baidu.com/s?ie=utf-8&wd=" + keyword
        urls.append(url)
    return urls


def get_urls_of_baidu(urls):
    removed_invalid_url = []

    # get information from baidu

    for url in urls:
        try:
            valid_urls = list_url_in_baidu(url)
        except Exception:
            traceback.print_exc()
            continue
        removed_invalid_url.extend(valid_urls)

    return removed_invalid_url


def list_url_in_baidu(url):
    valid_urls = []

    # set timeout and turnoff ssl
    r = requests.get(url, headers=http_tools.HttpTool().rand_user_agent_of_header(),
                     timeout=2, verify=False)
    if r.status_code == 200:

        html_doc = r.content.decode(chardet.detect(r.content)['encoding'])

        soup = BeautifulSoup(html_doc, 'html.parser')

        b_content = soup.find('div', id='content_left')

        list1 = b_content.find_all('a', href=True)

        for elem in list1:
            url = elem['href']
            if url.startswith('https') or url.startswith('http'):
                valid_urls.append(url)
                # removed_invalid_url.append(url)

        for elem in list1:
            attrs = elem.attrs
            if hasattr(attrs, 'data-url'):
                url = elem['data-url']
                valid_urls.append(url)

    return valid_urls


def separate_direct_indirect_list(removed_invalid_url):
    # remove same elements
    removed_invalid_url_set = set(_flatten(removed_invalid_url))
    url_direct_list = []
    url_redirect_list = []
    for url in removed_invalid_url_set:
        if "link?url=" in url:
            url_redirect_list.append(url)
        else:
            url_direct_list.append(url)
    return url_direct_list, url_redirect_list


def generate_html_list(url_direct_list, url_redirect_list):
    html_list = []

    # operate respectively
    html_direct_list2 = list_html_direct_location(url_direct_list)

    html_list.extend(html_direct_list2)
    html_list = list(filter(None, html_list))

    html_indirect_list2 = list_html_redirect_location(url_redirect_list)

    html_list.extend(html_indirect_list2)
    html_list = list(filter(None, html_list))

    return html_list


def list_html_direct_location(url_list):
    html_list = []
    for url in url_list:

        response_content = None

        try:
            response = requests.get(url, headers=http_tools.HttpTool().rand_user_agent_of_header(),
                                    timeout=2)
            # decode
            response_content = response.content.decode(chardet.detect(response.content)['encoding'])


        except (requests.exceptions.ConnectionError, ReadTimeout):
            print("Direct connection is timeout!")
            continue
        except (UnicodeDecodeError):
            print("UnicodeDecodeError")
            continue
        except Exception:
            traceback.print_exc()
            continue

        html_list.append(response_content)
    return html_list


def list_html_redirect_location(url_list):
    html_list = []
    for url in url_list:

        res = None
        try:
            # turn off redirect function
            res = requests.get(url=url, allow_redirects=False,
                               headers=http_tools.HttpTool().rand_user_agent_of_header(),
                               timeout=2)

            if (res is not None) and (res.status_code == 302):
                direct_url = res.headers['location']

                response = None
                response = requests.get(direct_url, allow_redirects=False,
                                        headers=http_tools.HttpTool().rand_user_agent_of_header(),
                                        timeout=2)

            if (response is not None) and (response.status_code == 200):
                html = response.content.decode(chardet.detect(response.content)['encoding'])
                html_list.append(html)

        except (requests.exceptions.ConnectionError, ReadTimeout):
            print("Reptile original website is failure!")
            continue
        except UnicodeDecodeError:
            print("UnicodeDecodeError")
            continue
        except Exception:
            traceback.extract_stack()
            continue

    return html_list


def convert_html_txt(html_list):
    # remove same html by default hashcode
    html_list = list(set(html_list))
    text_list = []
    for html in html_list:
        soup = BeautifulSoup(html, 'html.parser')

        text = soup.text

        # remove javascript and css
        info = [s.extract() for s in soup('script')]

        for script_content in info:
            text = text.replace(script_content.text, '')

        css_content = [s.extract() for s in soup('style')]

        for css in css_content:
            text = text.replace(css.text, '')

        text_list.append(text)

    return text_list


def clean_data(html_list):
    html_list_cleaned = []

    for html in html_list:
        # clean program language
        html_str = cd.clean_data(html)

        if '' is not html_str:
            html_list_cleaned.append(html_str)

    return html_list_cleaned


def main_operator(files_path, file_name):
    # generate urls of request of baidu from txt file
    file_name = file_name + '.txt'
    file_absolute_path = files_path + '/' + file_name

    urls = generate_request_baidu_url(file_absolute_path)

    # get source from baidu
    removed_invalid_url = get_urls_of_baidu(urls)
    if len(removed_invalid_url) < 1:
        raise Exception('there is nothing in removed_invalid_url')

    # separate_direct_indirect_list
    url_direct_list, url_redirect_list = separate_direct_indirect_list(removed_invalid_url)
    html_list = generate_html_list(url_direct_list, url_redirect_list)

    # get pure text
    html_text = convert_html_txt(html_list)
    # file_fpath = files_path + "/" + file_name_separated[0]

    # clean data
    pure_text = clean_data(html_text)

    parent_file_path = os.path.dirname(files_path)
    file_name_separated = file_name.split('.')
    file_fpath = parent_file_path + "/" + file_name_separated[0]

    if not os.path.exists(file_fpath):
        os.mkdir(file_fpath)
        os.chdir(file_fpath)

        # write files
        for i in range(len(pure_text)):
            with open(str(i + 1) + '.txt', 'w+') as html_content_file:
                html_content_file.write(pure_text[i])
    else:
        return


# filter files which have been processed
def filter_files(files_path, parent_file_path):
    folder_name = [f for f in os.listdir(parent_file_path)]
    files_name = [f.split('.')[0] for f in os.listdir(files_path) if isfile(join(files_path, f))]
    return [file for file in files_name if file not in folder_name]


# main function
if __name__ == '__main__':

    files_path = input('files_path (case sensitive):')
    parent_file_path = os.path.dirname(files_path)

    os.chdir(files_path)

    # filter files which have been processed
    file_list_name = filter_files(files_path, parent_file_path)

    # generate 5 process

    # multi_pool = Pool(2)
    for file_name in file_list_name:
        try:
            print("The current processing file :", file_name)
            main_operator(files_path, file_name)
            # multi_pool.apply_async(main_operator, args=(files_path, file_name))
            # print('Waiting for all subprocesses done...')
        except Exception as ex:
            traceback.print_exc()
            continue
    # multi_pool.close()
    # multi_pool.join()
    # print('All subprocesses done.')

# /Users/geekye/Documents/Dataset/CV_set/gt
