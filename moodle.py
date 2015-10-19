#!/usr/bin/env python
from requests import session
import click
import engine
import re
import os
import shelve
from keys import USERNAME, PASSWORD

LOGIN_PAGE = "https://moodle2.gla.ac.uk/login/index.php"
HOME_PAGE = "http://moodle2.gla.ac.uk/my/"
payload = {
    'action': 'login',
    'username': USERNAME,
    'password': PASSWORD
}


@click.command()
def main():
    with session() as c:
        click.echo("Logging in with username {}...".format(USERNAME))  # Create moodle session
        response = c.post(LOGIN_PAGE, data=payload)
        response.raise_for_status()
        click.echo("Login successful!")

        click.echo("Getting course list...")
        course_list = engine.get_courses(c, HOME_PAGE)

        click.echo("-----")
        click.echo("The following courses were found:")
        for i, course in enumerate(course_list):
            click.echo("{}: {}".format(i+1, course.name))
        click.echo("Enter numbers separated by commas or dashes to denote a range (no spaces).")
        click.echo("e.g. 3,4,6-10")
        options = []
        while True:
            choice = click.prompt("Which modules do you want to download lectures for?", type=str)
            success, options = main_validate_course(choice, len(course_list))
            if success:
                click.echo("Selected modules: {}".format(', '.join([str(x) for x in options])))
                if click.confirm("Download lectures for selected modules?"):
                    break
                click.confirm("Start over?", abort=True)
            else:
                click.echo(options)
        with shelve.open('data') as db:
            choice = click.prompt("Type a destination directory. Last used:",
                                  default=db.get("dest_dir", ""))
            db["dest_dir"] = choice  # No validation performed!
        base_dir = os.path.expanduser(choice)

        # Make a list of selected modules
        to_dl = [course_list[option-1] for option in options]

        click.echo("-----")
        click.echo("Base directory: {}".format(base_dir))

        running_total = 0
        # Iterate over to_dl, downloading lectures
        for course in to_dl:
            click.echo("-----")
            click.echo("Getting lecture download pages for {}".format(course.name))
            engine.get_weeks_lecture_page(c, course)

            for page in course.lecture_pages:
                click.echo("Downloading lectures for {}:".format(page[0]))
                dest = os.path.join(base_dir, course.name, page[0], "Lectures")
                os.makedirs(dest, exist_ok=True)
                running_total = engine.get_files(c, dest, page[1], running_total)

        click.echo("Download complete! {} files downloaded.".format(running_total))


def main_validate_course(choice, num_courses):  # TODO: Validate against available courses
    choice = "".join(choice.split())
    match = re.match("^(\d+(-\d+)?)(,\s*\d+(-\d+)*)*$", choice)
    output = []
    if match is not None:  # Matched! Valid input provided
        options = choice.split(",")
        for option in options:
            if option.isdigit():  # Input is a digit, not a range
                if int(option) not in range(1, num_courses+1):  # Check that the choice corresponds to a valid course
                    return False, "Invalid choice: {}".format(option)
                output.append(int(option))
            else:  # Input is a range e.g. 4-10
                tmp = option.split("-")
                for i in range(int(tmp[0]), int(tmp[1])+1):
                    if i not in range(1, num_courses+1):
                        return False, "Invalid choice: {}".format(i)
                    output.append(i)
    else:  # No match!
        return False, "Invalid input!"
    output = list(set(output))  # remove duplicates
    output.sort()  # sort list
    return True, output

if __name__ == '__main__':
    main()
