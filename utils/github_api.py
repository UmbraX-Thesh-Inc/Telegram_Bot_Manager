import requests
import base64
import zipfile
import io
import os
from config.settings import GITHUB_TOKEN, GITHUB_USERNAME

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}
BASE_URL = 'https://api.github.com'


def create_repository(name: str, description: str = '', private: bool = False) -> dict:
    url = f'{BASE_URL}/user/repos'
    data = {
        'name': name,
        'description': description,
        'private': private,
        'auto_init': True
    }
    r = requests.post(url, json=data, headers=HEADERS)
    return r.json(), r.status_code


def list_repositories(page: int = 1) -> list:
    url = f'{BASE_URL}/user/repos?per_page=10&page={page}&sort=updated'
    r = requests.get(url, headers=HEADERS)
    return r.json(), r.status_code


def search_repositories(query: str) -> list:
    url = f'{BASE_URL}/search/repositories?q={query}&sort=stars&per_page=10'
    r = requests.get(url, headers=HEADERS)
    return r.json(), r.status_code


def fork_repository(owner: str, repo: str) -> dict:
    url = f'{BASE_URL}/repos/{owner}/{repo}/forks'
    r = requests.post(url, headers=HEADERS)
    return r.json(), r.status_code


def delete_repository(repo: str) -> int:
    url = f'{BASE_URL}/repos/{GITHUB_USERNAME}/{repo}'
    r = requests.delete(url, headers=HEADERS)
    return r.status_code


def get_repo_info(owner: str, repo: str) -> dict:
    url = f'{BASE_URL}/repos/{owner}/{repo}'
    r = requests.get(url, headers=HEADERS)
    return r.json(), r.status_code


def get_repo_contents(owner: str, repo: str, path: str = '') -> list:
    url = f'{BASE_URL}/repos/{owner}/{repo}/contents/{path}'
    r = requests.get(url, headers=HEADERS)
    return r.json(), r.status_code


def upload_file_to_repo(repo: str, file_path: str, content: bytes, message: str = 'Upload via bot') -> dict:
    url = f'{BASE_URL}/repos/{GITHUB_USERNAME}/{repo}/contents/{file_path}'
    # Check if file exists
    check = requests.get(url, headers=HEADERS)
    data = {
        'message': message,
        'content': base64.b64encode(content).decode('utf-8')
    }
    if check.status_code == 200:
        data['sha'] = check.json()['sha']
    r = requests.put(url, json=data, headers=HEADERS)
    return r.json(), r.status_code


def get_file_content(owner: str, repo: str, path: str) -> dict:
    url = f'{BASE_URL}/repos/{owner}/{repo}/contents/{path}'
    r = requests.get(url, headers=HEADERS)
    return r.json(), r.status_code


def update_file_content(repo: str, path: str, content: str, sha: str, message: str = 'Update via bot') -> dict:
    url = f'{BASE_URL}/repos/{GITHUB_USERNAME}/{repo}/contents/{path}'
    data = {
        'message': message,
        'content': base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        'sha': sha
    }
    r = requests.put(url, json=data, headers=HEADERS)
    return r.json(), r.status_code


def download_repo_zip(owner: str, repo: str, branch: str = 'main') -> bytes:
    url = f'{BASE_URL}/repos/{owner}/{repo}/zipball/{branch}'
    r = requests.get(url, headers=HEADERS, allow_redirects=True)
    if r.status_code != 200:
        # try master
        url = f'{BASE_URL}/repos/{owner}/{repo}/zipball/master'
        r = requests.get(url, headers=HEADERS, allow_redirects=True)
    return r.content, r.status_code


def update_repo_settings(repo: str, **kwargs) -> dict:
    url = f'{BASE_URL}/repos/{GITHUB_USERNAME}/{repo}'
    r = requests.patch(url, json=kwargs, headers=HEADERS)
    return r.json(), r.status_code


def get_user_info() -> dict:
    url = f'{BASE_URL}/user'
    r = requests.get(url, headers=HEADERS)
    return r.json(), r.status_code


def list_branches(owner: str, repo: str) -> list:
    url = f'{BASE_URL}/repos/{owner}/{repo}/branches'
    r = requests.get(url, headers=HEADERS)
    return r.json(), r.status_code


def create_branch(repo: str, branch_name: str, from_branch: str = 'main') -> dict:
    # Get SHA of source branch
    url = f'{BASE_URL}/repos/{GITHUB_USERNAME}/{repo}/git/ref/heads/{from_branch}'
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        url = f'{BASE_URL}/repos/{GITHUB_USERNAME}/{repo}/git/ref/heads/master'
        r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return r.json(), r.status_code
    sha = r.json()['object']['sha']
    create_url = f'{BASE_URL}/repos/{GITHUB_USERNAME}/{repo}/git/refs'
    data = {'ref': f'refs/heads/{branch_name}', 'sha': sha}
    r2 = requests.post(create_url, json=data, headers=HEADERS)
    return r2.json(), r2.status_code
