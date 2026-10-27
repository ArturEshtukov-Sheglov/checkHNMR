# Installing and running checkHNMR on your computer

This guide assumes you have never used Python or a terminal. It takes about 10–15 minutes the first time;
later runs are a double-click.

You need: a computer with Windows 10/11, macOS or Linux, about 1 GB of free disk space, and an internet
connection (for installing the packages and for making structures from compound names).

---

## Windows

### Step 1. Install Python (once)

1. Open <https://www.python.org/downloads/> and click the yellow button **Download Python 3.x.x**
   (any version 3.10 or newer).
2. Run the downloaded file.
3. **Important:** in the first window of the installer, tick the box **Add python.exe to PATH** at the bottom.
   Then click **Install Now**.
4. When the installer says "Setup was successful", click **Close**.

### Step 2. Download checkHNMR (once)

1. On the GitHub page of checkHNMR, click the green **Code** button, then **Download ZIP**.
2. Find the file `checkHNMR-main.zip` in your Downloads folder, right-click it and choose **Extract All…**.
3. Move the extracted folder to a place with a short path, for example `C:\checkHNMR`.
   (Very long folder paths can cause problems in Windows.)

### Step 3. Put your files in

Copy the PDF files you want to check into the folder `data` inside the checkHNMR folder:
Supporting Information files, or a PDF made from the checkHNMR template. Any file names are fine.
A Word file must first be saved as PDF (File → Save As → PDF); scanned pages cannot be read.

### Step 4. Run

1. Double-click **`run_all.bat`**.
2. If Windows shows "Windows protected your PC", click **More info**, then **Run anyway**
   (this appears for files downloaded from the internet).
3. The first time, a black window says that some packages are missing and asks
   `Install them now? [y/n]`. Type **y** and press **Enter**. The installation takes a few minutes.
4. The files are then checked one after another. When the window says **Done**, press any key to close it.

### Step 5. Read the results

Open the folder `results`. For every PDF there is a folder with its name, and in it:

- **`checked_<file name>.docx`** — the Word report: one compound per page, with the structure, the description
  (flagged signals coloured) and the verdict for every checklist item. Start here.
- `checked_<file name>.xlsx` — the same results as a table with all columns.

Next time, skip steps 1–2: put new files into `data` and double-click `run_all.bat` again.
Files already checked are skipped; to check them again, delete their folder in `results`.

---

## macOS

1. **Install Python:** download the macOS installer from <https://www.python.org/downloads/> and run it.
   At the end, the installer opens a folder; double-click **Install Certificates.command** in it
   (without this, the connection to the OPSIN web service can fail).
2. **Download checkHNMR:** green **Code** button → **Download ZIP**; double-click the zip file to unpack it.
3. **Put your PDF files** into the folder `data`.
4. **Run:** open the app **Terminal** (Applications → Utilities), type `bash ` (with a space at the end), drag the
   file `run_all.sh` from the checkHNMR folder into the Terminal window and press **Enter**.
   The first time, answer **y** when asked to install the packages.
5. **Read the results** in the folder `results`, as in step 5 for Windows.

## Linux

1. Install Python 3.10 or newer if it is not there:
   `sudo apt install python3 python3-pip python3-venv` (Debian/Ubuntu) or `sudo dnf install python3 python3-pip` (Fedora).
2. Download and unpack checkHNMR (green **Code** button → **Download ZIP**, or `git clone`).
3. Put your PDF files into `data` and run `bash run_all.sh` in the checkHNMR folder; answer **y** when asked to
   install the packages. Where the system does not allow installing packages into its own Python, they are
   installed into a folder `.venv` next to the scripts, and later runs use it automatically.
4. Read the results in `results`.

---

## Checking that the installation works

Double-click **`run_tests.bat`** (Windows) or run `bash run_tests.sh` (macOS, Linux). It needs no files and
takes a few minutes. At the end it prints a table; the last line should be **ALL PASSED**.

## If something goes wrong

| Message | What to do |
|---|---|
| "Python was not found on this computer" | Install Python (step 1). On Windows, the box "Add python.exe to PATH" must be ticked; if it was not, run the installer again, choose **Modify** and tick it, or uninstall and install again |
| "There are no PDF files in the folder data" | Put the PDF files into the folder `data` inside the checkHNMR folder (not into its parent folder) |
| "The OPSIN web service does not answer" | The computer is offline, or the service is down. The descriptions are then checked from the text only. Start `run_all` again when online: these files are done again with structures |
| The package installation fails | Check the internet connection and start again. The message shows the exact command to run by hand |
| A file gives 0 descriptions | The PDF may be a scan or a picture of text (text that cannot be selected), or the descriptions may be written in an unusual form. See `results\run_log.txt` |

Details of every step of a run are in `results\run_log.txt`.

## Without installing anything

Open the notebook directly in Google Colab: **[Open in Colab](https://colab.research.google.com/github/ArturEshtukov-Sheglov/checkHNMR/blob/main/run_all_Colab.ipynb)**
(a Google account is needed). Run its three cells one after another (the ▶ button on the left of each cell), upload the PDF files when asked and download the results. The files are
processed on Google servers: fine for published SI; for unpublished data use the local version.
