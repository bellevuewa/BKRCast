import datetime
import os, sys, time
import nbformat
import yaml
import shutil
from nbconvert.preprocessors import ExecutePreprocessor
from input_configuration import project_folder, run_bkrcast_summary
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from data_wrangling import open_main_logger

def run_ipynb(sheet_name, nb_path):
    start_time = time.time()
    print("creating " + sheet_name + " page")
    with open(os.path.join(project_folder, nb_path, sheet_name + ".ipynb"), "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
        if sys.version_info > (3, 0):
            py_version = "python3"
        else:
            py_version = "python2"
        ep = ExecutePreprocessor(timeout=1500, kernel_name=py_version)
        ep.preprocess(nb, {"metadata": {"path": nb_path}})
        with open(os.path.join(project_folder, nb_path, sheet_name + ".ipynb"), "wt", encoding="utf-8") as f:
            nbformat.write(nb, f)
    end_time = time.time()
    print(f"Time taken to create {sheet_name} page: {end_time - start_time:.1f} seconds")


def create_quarto_notebook(notebook_name, summary_list, scripts_dir, output_folder):

    for sheet_name in summary_list:
        run_ipynb(sheet_name, scripts_dir)
    print(f'Rendering {notebook_name} tables...')

    # render quarto book
    text = "quarto render " + scripts_dir
    os.system(text)

    # remove existing data first
    output_dir = os.path.join(project_folder, 'outputs', 'summary', output_folder)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    # move these files to output folder
    qproduct_folder = os.path.join(project_folder, scripts_dir, output_folder)
    if not os.path.exists(qproduct_folder):
        os.makedirs(qproduct_folder)
    shutil.move(qproduct_folder, output_dir)

    print(f'To open the BKRCast Summary, go to {output_dir} and double click on "index.html"')


def main():
    # create summary notebook
    if run_bkrcast_summary:
        # copy all files from templates folder to scripts/summarize/calibration/notebooks
        templates_folder = os.path.join(project_folder, 'scripts', 'summarize', 'calibration', 'notebooks', 'templates')
        target_folder = os.path.join(project_folder, 'scripts', 'summarize', 'calibration', 'notebooks')
        for item in os.listdir(templates_folder):
            s = os.path.join(templates_folder, item)
            d = os.path.join(target_folder, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)

        qfile = os.path.join(project_folder, r'scripts\summarize\calibration\notebooks\_quarto.yml')
        if not os.path.exists(qfile):
            raise FileNotFoundError(f"{qfile} not found")

        with open(qfile, "r", encoding="utf-8") as f:
            qcfg = yaml.safe_load(f) or {}

        # locate chapters list in common places
        chapters = [chapter.split('.')[0] for chapter in qcfg['book']['chapters'] if '.qmd' not in chapter]

        create_quarto_notebook(notebook_name = "bkrcast_validation",
                               summary_list = chapters,
                               scripts_dir = r"scripts\summarize\calibration\notebooks", 
                               output_folder = qcfg['project']['output-dir']) 

if __name__ == "__main__":
    run_context = os.getenv('RUN_CONTEXT') # chained if this script is called from another script, otherwise it is standalone
    if run_context == 'chained':
        meta_data = False
    else:
        meta_data = True

    logger, start_time = open_main_logger(meta_data, 'Data Processing')
    logger.info(f"Running script: {os.path.basename(__file__)} %s", " ".join(sys.argv[1:]))
    main()
    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info(f'Total run time: {elapsed_total}')