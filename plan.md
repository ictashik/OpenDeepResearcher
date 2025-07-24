Project: AI-Powered Systematic Review & Research Application
Role: You are an expert Python developer specializing in building clean, scalable, and interactive data applications with Streamlit.

High-Level Goal: Construct a multi-page Streamlit application that functions as a "Systematic Review Generator & Deep Research Tool." The application must follow a sequential, human-in-the-loop workflow, breaking down the complex research process into manageable, user-approved steps.

1. Core Philosophy & UI/UX Design
UI Inspiration: The user interface must be clean, minimalist, and highly functional. Take inspiration from the aesthetics of shadcn/ui and the layout of Visual Studio Code. Avoid large blocks of text; use icons, expanders, and well-organized components.

Layout:

Main Sidebar (Navigation): A persistent sidebar on the left for navigating between projects and the main steps of the review process.

Main Content Area: The central part of the app where the user interacts with the current step.

Log Panel (Footer): A persistent, expandable log panel at the bottom of the window (st.expander) that provides real-time, timestamped feedback on all background processes. This is critical for user trust and transparency.

Interactivity: The application must be project-based and stateful. The user's progress within a project must be saved automatically at each step. Use interactive components like st.data_editor for screening/verification and st.file_uploader for manual uploads.

2. Technical Stack & Architecture
Frontend/App Framework: Streamlit

Backend Logic: Python

Data Storage:

Use Pandas DataFrames and CSV files for all structured data.

Store uploaded/downloaded articles as PDF files.

LLM Integration: Use the requests library to connect to an Ollama API endpoint. The endpoint URL must be configurable.

PDF Processing: Use the PyMuPDF library for parsing PDFs and extracting text from specific sections.

Directory Structure: The application must manage projects using the following file structure:

/data/
|
├── projects.csv
├── config.json
|
└─── /project_id_1/
|    ├── articles_raw.csv
|    ├── articles_screened.csv
|    ├── data_extracted.csv
|    ├── final_report.md
|    └─── /uploads/
|         └─── paper.pdf
|
└─── /project_id_2/
     ...

3. Sequential Feature Implementation Plan
Build the application in the following order. Each feature should be a distinct, functional module.

Step 0: Foundational Setup

Create the main app.py file.

Set up the basic multi-page layout with a sidebar and a placeholder for the main content area and the bottom log panel.

Create the /data directory.

Step 1: Configuration & Logging

Create a "Settings" page.

On this page, add input fields for:

Ollama Endpoint URL.

(Optional) API Key field (type="password").

Add a "Test & Fetch Models" button that, on success, populates dropdowns for selecting models for different tasks (e.g., "Screening Model," "Extraction Model").

Save these settings to config.json.

Implement the logging functionality. Create a logging utility that writes timestamped messages to the expandable log panel at the bottom of the screen.

Step 2: Project Management

On the main "Dashboard" page, implement logic to:

Read projects.csv. If it doesn't exist, create it.

Display a list of existing projects in a dropdown or list.

Provide a "Create New Project" button. This should create a new entry in projects.csv and a corresponding project_id folder.

Use Streamlit's session state (st.session_state) to manage the currently loaded project.

Step 3: Phase 1 - Scoping & Planning

Create a "Scoping" page.

Implement the UI for:

Problem Formulation: A text area for the user's research question. A button that calls the LLM to break it down into the PICO framework.

Keyword Generation: A section where the LLM generates keywords based on PICO. The user must be able to edit, add, or remove these keywords in a st.data_editor.

Source Selection: A simple interface (e.g., checkboxes) for the user to select which online sources to search (e.g., PubMed, Google Scholar).

Step 4: Phase 2 - Data Collection

Create a "Screening" page.

Implement the web scraping logic (you can start with a placeholder function that creates dummy article data).

The results should be saved to articles_raw.csv in the project folder.

The core of this page is an interactive table (st.data_editor) displaying the scraped articles.

Add a button to "Run AI Screening." This will use the LLM to read the title/abstract and add a new "AI Recommendation" (Include/Exclude) column.

The user makes the final decision using checkboxes in the table. The results are saved to articles_screened.csv.

Step 5: Phase 3 - Deep Analysis

Create a "Full-Text Analysis" page.

Display the list of articles from articles_screened.csv.

For each article, show its Full-Text Status (Awaiting, Acquired, Abstract Only).

Implement a button to "Attempt to Download Full Text" (can be a placeholder).

Next to each article, place a st.file_uploader to allow manual PDF uploads.

Implement the Targeted Data Extraction logic:

This process should iterate through all articles with acquired full text.

For each article, it will parse the PDF using PyMuPDF to identify sections.

It will then use the customizable prompts (from Settings) to query the relevant text sections via the LLM.

The extracted data is saved to data_extracted.csv.

Display the contents of data_extracted.csv in a final verification table for the user to review.

Step 6: Phase 3 - Reporting

Create a "Report" page.

Add a "Generate Report" button. This will send the clean, structured data from data_extracted.csv to the LLM to synthesize a full narrative report in Markdown format.

Display the generated report in a large st.text_area.

Provide "Save" and "Export" buttons.

4. Code Quality
Modularity: Write clean, modular code. Use functions and classes extensively. Avoid putting all logic in the main app.py. Create helper files (e.g., utils.py, ollama_client.py).

Comments & Docstrings: Add clear comments and docstrings to explain complex logic, especially for the LLM interaction and data processing steps.

Error Handling: Implement robust error handling (e.g., try-except blocks) for API calls, file operations, and web scraping. Log all errors to the log panel.