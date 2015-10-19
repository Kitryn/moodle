from requests import session
import os
import click
from urllib.parse import unquote
from bs4 import BeautifulSoup
import re


class Course(object):
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.lecture_pages = []


def get_soup(sess, url):  # DRY
    response = sess.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup


def get_courses(sess, home):  # Gets a list of all courses on the home page
    soup = get_soup(sess, home)
    raw_courses = soup.find_all("h2", class_=re.compile("title"))  # List of all courses on the main page
    course_list = []

    for course in raw_courses:  # Create Course objects for each course
        course_list.append(Course(course.string, course.a['href']))

    return course_list


def get_weeks_lecture_page(sess, course):  # Updates Course object with list of URLS to each week's lecture
    soup = get_soup(sess, course.url)  # Gets course page
    # Get all weeks
    weeks = soup.find_all("li", attrs={"id": re.compile("section-[0-9]"), "aria-label": re.compile("Week [0-9]")})
    for week in weeks:  # Separates between weeks being in own page, and weeks being on main page
        tmp = week.find(string="Lectures")  # Attempt to find Lectures in the week
        if tmp is None:  # Case: Each week is in its own page
            week_page = week.find('a', string=re.compile("Week [0-9]"))["href"]  # Get URL for the week page
            sub_soup = get_soup(sess, week_page)  # Open the week page
            lecture_page_url = sub_soup.find(string=re.compile("Lectures")).find_parent('a')["href"]  # Get Lecture URL
            week_name = " ".join(week["aria-label"].split()[:2])

            course.lecture_pages.append((week_name, lecture_page_url))  # [{"Week 1" : "http..."}, ...]
        else:  # Case: Each week is on the main page
            lecture_page_url = tmp.find_parent('a')["href"]  # Get Lecture page URL
            week_name = " ".join(week["aria-label"].split()[:2])
            course.lecture_pages.append((week_name, lecture_page_url))  # [{"Week 1" : "http..."}, ...]


def download_file(sess, destination, url):
    local_filename = unquote(url.split('/')[-1].split('?')[0])
    complete_name = os.path.join(os.path.expanduser(destination), local_filename)

    r = sess.get(url, stream=True)
    with open(complete_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return local_filename


def get_files(sess, destination, url, running=None):  # Downloads all files given a folder page unless it already exists
    soup = get_soup(sess, url)
    to_dl = soup.find_all("a", href=re.compile("forcedownload"))

    current = 1
    total_num = len(to_dl)
    for link in to_dl:
        filename = unquote(link["href"].split('/')[-1].split('?')[0])
        if os.path.isfile(os.path.join(os.path.expanduser(destination), filename)):
            click.echo("({}/{}) File already exists! Skipping {}".format(current, total_num, filename))
        else:
            click.echo("({}/{}) Downloading: {}".format(current, total_num, filename))
            download_file(sess, destination, link["href"])
            if running is not None:
                running += 1
        current += 1
    return running
