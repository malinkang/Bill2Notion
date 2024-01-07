import os
import re
import requests
from github import Github
from zipfile import ZipFile

# Initialize GitHub API client
g = Github(os.getenv('GITHUB_TOKEN'))
repo = g.get_repo(os.getenv('GITHUB_REPOSITORY'))
issue_number = os.environ.get('ISSUE_NUMBER') or os.environ.get('GITHUB_REF').split('/')[-1]
issue = repo.get_issue(number=int(issue_number))

# Find zip file URL in the issue body or comments
zip_url = None
if re.search(r'https?://\S+\.zip', issue.body):
    zip_url = re.search(r'https?://\S+\.zip', issue.body).group()

if not zip_url:
    for comment in issue.get_comments():
        if re.search(r'https?://\S+\.zip', comment.body):
            zip_url = re.search(r'https?://\S+\.zip', comment.body).group()
            break

if zip_url:
    # Download the zip file
    r = requests.get(zip_url)
    zip_path = 'downloaded.zip'
    with open(zip_path, 'wb') as zip_file:
        zip_file.write(r.content)

    # Unzip the file using the password from secrets
    with ZipFile(zip_path) as zip_ref:
        zip_ref.extractall(pwd=os.getenv('ZIP_PASSWORD').encode())
        # Print the list of file names
        print('Contents of the zip file:')
        for file_info in zip_ref.infolist():
            print(file_info.filename)

    print('Zip file downloaded and extracted.')
else:
    print('No zip file URL found in issue body or comments.')
