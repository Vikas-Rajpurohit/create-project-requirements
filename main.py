import streamlit as st
import os
import tempfile

from utils import extract_zip, download_github_repo, analyze_project, create_requirements, plot_dependency_graph

def main():
    # Configure page
    st.set_page_config(page_title="📦 Python Project Analyzer", layout="wide")

    st.title("📦 Python Project Analyzer")

    option = st.radio("Choose input method:", ["Upload ZIP", "GitHub Repo URL"])

    temp_dir = tempfile.mkdtemp()

    if option == "Upload ZIP":
        uploaded_file = st.file_uploader("Upload a ZIP file of your project", type=["zip"])
        if uploaded_file:
            extract_zip(uploaded_file, temp_dir)
            st.success("Project extracted successfully!")

    elif option == "GitHub Repo URL":
        github_url = st.text_input("Enter GitHub Repository URL")
        if st.button("Fetch Repo") and github_url:
            download_github_repo(github_url, temp_dir)
            st.success("Repository downloaded & extracted successfully!")

    # Run analysis
    if os.listdir(temp_dir):
        if st.button("Analyze Project"):
            dependencies, external_modules = analyze_project(temp_dir)

            # st.subheader("📂 File Dependency Graph")
            # if dependencies:
            #     plot_dependency_graph(dependencies)

            st.subheader("📜 requirements.txt")
            requirements = create_requirements(external_modules)
            st.code(requirements, language="text")

            st.download_button(
                label="⬇️ Download requirements.txt",
                data=requirements,
                file_name="requirements.txt",
                mime="text/plain"
            )


if __name__ == "__main__":
    main()
