import requests
import datetime
import urllib
import yaml
from rsfc.utils import constants

class GithubHarvester:
    
    def __init__(self, repo_url):
        self.repo_url =  repo_url
        self.repo_type = self.get_repo_type()
        self.api_url = self.get_repo_api_url()
        self.repo_branch = self.get_repo_default_branch()
        self.version = self.get_soft_version()
        self.cff = self.get_cff_file()
        self.codemeta = self.get_codemeta_file()
        self.commits = self.get_commits()
        self.issues = self.get_issues()
        self.tests = self.get_tests()
    
    
    def get_repo_api_url(self):
        parsed_url = urllib.parse.urlparse(self.repo_url)
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError("Error when parsing repository API URL")

        owner, repo = path_parts[-2], path_parts[-1]

        if self.repo_type == constants.REPO_TYPES[0]:
            url = f"https://api.github.com/repos/{owner}/{repo}"
        elif self.repo_type == constants.REPO_TYPES[1]:
            project_path = urllib.parse.quote(f"{owner}/{repo}", safe="")
            url = f"https://gitlab.com/api/v4/projects/{project_path}"
        else:
            raise ValueError("URL not within supported types (Github and Gitlab)")

        return url
    
    
    def get_repo_type(self):
        if "github" in self.repo_url:
            repo_type = constants.REPO_TYPES[0]
        elif "gitlab" in self.repo_url:
            repo_type = constants.REPO_TYPES[1]
            
        return repo_type
    
    
    def get_repo_default_branch(self):
        res = requests.get(self.api_url)
        res.raise_for_status()
        data = res.json()
        return data.get("default_branch", "main")
    
    
    def get_codemeta_file(self):
        req_url = self.api_url + '/contents/codemeta.json'
        
        try:
            if self.repo_type == "GITHUB":
                req_url = self.api_url + '/contents/codemeta.json'
                headers = {'Accept': 'application/vnd.github.v3.raw'}
                params = {'ref': self.repo_branch}

                response = requests.get(req_url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            elif self.repo_type == "gitlab":
                project_path_encoded = self.api_url.split("/projects/")[-1]
                branch = self.repo_branch or "main"
                req_url = f"https://gitlab.com/api/v4/projects/{project_path_encoded}/repository/files/codemeta.json/raw"
                params = {'ref': branch}
                response = requests.get(req_url, params=params)
                response.raise_for_status()
                return response.json()
            else:
                return None
            
        except requests.RequestException:
            return None
            
    def get_cff_file(self):
        
        try:
            if self.repo_type == "GITHUB":
                req_url = self.api_url + '/contents/CITATION.cff'
                headers = {'Accept': 'application/vnd.github.v3.raw'}
                params = {'ref': self.repo_branch}
                response = requests.get(req_url, headers=headers, params=params)
                response.raise_for_status()
                return yaml.safe_load(response.text)
            elif self.repo_type == "GITLAB":
                project_path_encoded = self.api_url.split("/projects/")[-1]
                branch = self.repo_branch or "main"
                req_url = f"https://gitlab.com/api/v4/projects/{project_path_encoded}/repository/files/CITATION.cff/raw"
                params = {'ref': branch}
                response = requests.get(req_url, params=params)
                response.raise_for_status()
                return yaml.safe_load(response.text)
            else:
                return None

        except requests.RequestException:
            return None
        
        
    def get_soft_version(self):
        try:
            releases_url = f"{self.api_url}/releases"

            response = requests.get(releases_url)
            response.raise_for_status()
            releases = response.json()

            latest_release = None
            latest_date = None

            for release in releases:
                if self.repo_type == "GITHUB":
                    date_str = release.get("published_at")
                    tag = release.get("tag_name")
                elif self.repo_type == "GITLAB":
                    date_str = release.get("released_at")
                    tag = release.get("tag_name")
                else:
                    raise ValueError("Unsupported repository type")

                if date_str and tag:
                    try:
                        dt = datetime.fromisoformat(date_str.rstrip("Z"))
                    except ValueError:
                        continue

                    if latest_release is None or dt > latest_date:
                        latest_release = tag
                        latest_date = dt

            return latest_release

        except Exception as e:
            print(f"Error fetching releases from {self.repo_type} at {releases_url}: {e}")
            return None
        
        
    def get_commits(self):
        if self.repo_type == "GITHUB":
            commits_url = self.api_url + "/commits"
            headers = {'Accept': 'application/vnd.github.v3.raw'}
            response = requests.get(commits_url, headers=headers)

        elif self.repo_type == "GITLAB":
            commits_url = f"{self.api_url}/repository/commits?ref_name={self.repo_branch}"
            response = requests.get(commits_url)

        else:
            raise ValueError(f"Repositorio no soportado: {self.repo_type}")

        if response.status_code == 200:
            commits = response.json()
        else:
            commits = []

        return commits
    
    
    def get_issues(self):
        if self.repo_type == "GITHUB":
            issues_url = self.api_url + "/issues?state=all"
            headers = {'Accept': 'application/vnd.github.v3.raw'}
            response = requests.get(issues_url, headers=headers)

        elif self.repo_type == "GITLAB":
            issues_url = f"{self.api_url}/issues?state=all"
            response = requests.get(issues_url)

        else:
            raise ValueError(f"Repositorio no soportado: {self.repo_type}")

        if response.status_code == 200:
            issues = response.json()
        else:
            issues = []

        return issues
    
    
    def get_tests(self):
        test_evidences = []

        if self.repo_type == "GITHUB":
            tree_url = f"{self.api_url}/git/trees/HEAD?recursive=1"
            resp = requests.get(tree_url, headers={'Accept': 'application/vnd.github.v3+json'})
            if resp.status_code == 200:
                test_evidences = resp.json().get("tree", [])

        elif self.repo_type == "GITLAB":
            tree_url = f"{self.api_url}/repository/tree?recursive=true&ref={self.repo_branch}&per_page=100"
            resp = requests.get(tree_url)
            if resp.status_code == 200:
                test_evidences = [{"path": item["path"]} for item in resp.json()]

        else:
            raise ValueError("Unsupported repository type")
        
        return test_evidences