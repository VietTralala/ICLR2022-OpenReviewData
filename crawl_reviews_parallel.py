import os
import sys
import time
import pickle
import pandas as pd
from tqdm import tqdm
from joblib import Parallel, delayed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options

import ipdb


def get_score(rawtext):
    try:
        score = int(rawtext.split(':')[1])
    except:
        score = None
    return score


def remove_first_line(rawtext):
    lines = rawtext.split('\n')[1:]
    return '\n '.join(lines)


def process_review(elem):
    review = dict()
    for x in elem.find_elements_by_xpath('./div[@class="note_contents"]'):
        if x.text.startswith('Summary Of The Paper:'):
            review['summary_paper'] = remove_first_line(x.text)
        elif x.text.startswith('Main Review:'):
            review['main_review'] = remove_first_line(x.text)
        elif x.text.startswith('Summary Of The Review:'):
            review['summary_review'] = remove_first_line(x.text)
        elif x.text.startswith('Correctness: '):
            review['correctness'] = get_score(x.text)
        elif x.text.startswith('Technical Novelty And Significance: '):
            review['techNS'] = get_score(x.text)
        elif x.text.startswith('Empirical Novelty And Significance: '):
            review['empNS'] = get_score(x.text)
        elif x.text.startswith('Flag For Ethics Review: '):
            if x.text.split(':')[-1] == ' NO.':
                review['flags_ethics'] = False
            else:
                review['flags_ethics'] = True
        elif x.text.startswith('Details Of Ethics Concerns: '):
            review['details_ethics'] = remove_first_line(x.text)
        elif x.text.startswith('Recommendation: '):
            review['recommendation'] = get_score(x.text)
        elif x.text.startswith('Confidence: '):
            review['confidence'] = get_score(x.text)

    return review


def crawl_single_review(row):
    link = row.link
    paper_id = row.name
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome('chromedriver', options=chrome_options)

    all_reviews = []

    try:
        driver.get(link)
        xpath = '//div[@id="note_children"]//span[@class="note_content_value"]/..'
        cond = EC.presence_of_element_located((By.XPATH, xpath))
        WebDriverWait(driver, 60).until(cond)

        xpath = '//div[@id="note_children"]//div[@class="note panel"]'
        elems = driver.find_elements_by_xpath(xpath)

        assert len(elems), 'empty ratings'

        # process elements:

        for elem in elems:
            review = process_review(elem)
            all_reviews.append(review)

    except Exception as e:
        print(paper_id, e)

    driver.close()

    return paper_id, all_reviews


if __name__ == "__main__":

    df = pd.read_csv('paperlist.tsv', sep='\t', index_col=0)

    # for idx, row in df.iterrows():
    #     paper_id, reviews = crawl_single_review(row)
    #     ipdb.set_trace()

    # parallel
    ids, reviews = zip(*Parallel(n_jobs=50)
                       (delayed(crawl_single_review)(row) for idx, row in tqdm(df.iterrows(), total=len(df))))
    reviews_of_all_papers = {i: rev for i, rev in zip(ids, reviews)}

    # print(reviews[:2])
    with open('reviews_of_all_papers2.pkl', 'wb') as f:
        pickle.dump(reviews_of_all_papers, f)
    # df = pd.DataFrame(ratings).T
    # df['decision'] = pd.Series(decisions)
    # df.index.name = 'paper_id'
    # df.to_csv('ratings.tsv', sep='\t')
