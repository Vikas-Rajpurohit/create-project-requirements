import streamlit as st
import os
import json
import zipfile
import requests
import ast
import importlib.metadata
import networkx as nx
import matplotlib.pyplot as plt
import sys

STD_LIBS = sys.stdlib_module_names  
def is_stdlib(module_name: str) -> bool:
    return module_name in STD_LIBS

IMPORTS_JSON = os.path.join(os.path.dirname(__file__), "imports.json")

with open(IMPORTS_JSON, "r") as f:
    IMPORT_TO_PYPI = json.load(f)

def extract_zip(uploaded_file, extract_dir):
    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)


def download_github_repo(github_url, extract_dir):
    try:
        if github_url.endswith("/"):
            github_url = github_url[:-1]

        repo_name = github_url.split("/")[-1]
        zip_url = github_url + "/archive/refs/heads/main.zip" 

        # Fetch repo zip
        r = requests.get(zip_url, stream=True, timeout=10)
        r.raise_for_status()  # raises HTTPError if status != 200

        zip_path = os.path.join(extract_dir, f"{repo_name}.zip")
        with open(zip_path, "wb") as f:
            f.write(r.content)

        # Extract zip
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        return True, f"Repository '{repo_name}' downloaded successfully."

    except requests.exceptions.RequestException as e:
        return False, f"Network error while downloading repo: {e}"
    except zipfile.BadZipFile:
        return False, "Downloaded file is not a valid zip archive."
    except Exception as e:
        return False, f"Unexpected error: {e}"


def analyze_project(project_path):
    print(project_path)
    py_files = []
    for root, _, files in os.walk(project_path):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))

    dependencies = {}
    external_modules = set()

    for file_path in py_files:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                node = ast.parse(f.read(), filename=file_path)
            except Exception:
                continue

        file_name = os.path.relpath(file_path, project_path)
        dependencies[file_name] = []

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    mod = alias.name.split(".")[0]
                    if any(mod in os.path.basename(f) for f in py_files):
                        dependencies[file_name].append(mod + ".py")
                    else:
                        external_modules.add(mod)

            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module:
                    mod = stmt.module.split(".")[0]
                    if any(mod in os.path.basename(f) for f in py_files):
                        dependencies[file_name].append(mod + ".py")
                    else:
                        external_modules.add(mod)

    return dependencies, external_modules

def create_requirements(external_modules):
    req_lines = []
    UNRESOLVED = set()

    for mod in sorted(external_modules):
        # Map import → PyPI name if known
        if is_stdlib(mod):
            continue
        
        pkg = IMPORT_TO_PYPI.get(mod, mod)

        try:
            version = importlib.metadata.version(pkg)
            req_lines.append(f"{pkg}=={version}")
        except importlib.metadata.PackageNotFoundError:
            try:
                response = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=5)
                if response.status_code == 200:
                    latest_version = response.json()["info"]["version"]
                    req_lines.append(f"{pkg}=={latest_version}")
                else:
                    req_lines.append(pkg)
                    UNRESOLVED.add(mod)   # log for review
            except Exception:
                req_lines.append(pkg)
                UNRESOLVED.add(mod)

   
    if UNRESOLVED:
        with open("unresolved_imports.log", "a") as f:
            for name in sorted(UNRESOLVED):
                f.write(name + "\n")

    return "\n".join(req_lines)



def plot_dependency_graph(dependencies):
    G = nx.DiGraph()
    for src, targets in dependencies.items():
        for tgt in targets:
            G.add_edge(src, tgt)

    plt.figure(figsize=(8, 6))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, with_labels=True, node_size=2000,
            node_color="lightblue", font_size=8, arrows=True)
    st.pyplot(plt)