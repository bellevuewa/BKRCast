import os, sys, time
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from input_configuration import project_folder, run_bkrcast_summary
import yaml


def run_ipynb(sheet_name, nb_path):
    start_time = time.time()
    print("creating " + sheet_name + " page")
    with open(os.path.join(project_folder, nb_path, sheet_name + ".ipynb")) as f:
        nb = nbformat.read(f, as_version=4)
        if sys.version_info > (3, 0):
            py_version = "python3"
        else:
            py_version = "python2"
        ep = ExecutePreprocessor(timeout=1500, kernel_name=py_version)
        ep.preprocess(nb, {"metadata": {"path": nb_path}})
        with open(os.path.join(project_folder, nb_path, sheet_name + ".ipynb"), "wt") as f:
            nbformat.write(nb, f)
    end_time = time.time()
    print(f"Time taken to create {sheet_name} page: {end_time - start_time:.1f} seconds")


def create_quarto_notebook(notebook_name, summary_list, scripts_dir, output_folder):

    for sheet_name in summary_list:
        run_ipynb(sheet_name, scripts_dir)

    # render quarto book
    text = "quarto render " + scripts_dir
    os.system(text)
    print(notebook_name + " created")
    print(f'To open the BKRCast Summary, go to {scripts_dir}\{output_folder} and double click "index.html"')


def main():
    # create summary notebook
    if run_bkrcast_summary:
        qfile = os.path.join(project_folder, r'scripts\summarize\calibration\notebooks\_quarto.yml')
        if not os.path.exists(qfile):
            raise FileNotFoundError(f"{qfile} not found")

        with open(qfile, "r", encoding="utf-8") as f:
            qcfg = yaml.safe_load(f) or {}

        # locate chapters list in common places
        chapters = [chapter.split('.')[0] for chapter in qcfg['book']['chapters'] if '.qmd' not in chapter]

        create_quarto_notebook(notebook_name = "bkrcast_summary-notebook",
                               summary_list = chapters,
                               scripts_dir = r"scripts\summarize\calibration\notebooks", 
                               output_folder = qcfg['project']['output-dir']) 

if __name__ == "__main__":
    main()