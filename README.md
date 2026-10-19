# DataScopia for Windows

Standalone Windows build of [DataScopia](https://github.com/boandme/kaggle_datasetAnalysis), a
research-focused open-source platform for exploring, analyzing, and understanding datasets from
Kaggle and Hugging Face with the help of intelligent automated analysis, interactive
visualizations, and an AI-assisted research workflow. See that repo for the full feature list,
the hosted web version, and the actual application source.

This repo holds only the Windows packaging: a PyInstaller spec and a GitHub Actions workflow that
checks out the main repo's source fresh on every build and packages it into a double-clickable
app. There's no copy of the app's source here to fall out of sync - whatever's on the main repo's
`main` branch is what gets built.

## Download

Grab the latest `DataScopia-windows.zip` from [Releases](../../releases), unzip it anywhere, and
run `DataScopia.exe`. It starts a local server and opens the app in your browser - no install step,
no admin rights needed. Your data (accounts, saved projects) is stored in
`%LOCALAPPDATA%\DataScopia`, not inside the app folder, so moving or deleting the unzipped folder
never touches it.

Kaggle search/analyze needs a Kaggle API token to work (Hugging Face, file upload, and the demo
dataset work with no setup at all): drop a `.env` file next to `DataScopia.exe` containing

```
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_api_key
```

(get these from [kaggle.com/settings](https://www.kaggle.com/settings) → API → Create New Token).

## Building it yourself

```powershell
git clone https://github.com/<your-username>/datascopia-desktop.git
cd datascopia-desktop
git clone https://github.com/boandme/kaggle_datasetAnalysis.git source
pip install -r source/requirements.txt pyinstaller>=6.22.0
pyinstaller packaging/datascopia.spec --clean
```

The result is in `dist_desktop/DataScopia/`. The GitHub Actions workflow
(`.github/workflows/build.yml`) does exactly this automatically and attaches the result to a
release whenever a tag (`vX.Y`) is pushed to this repo.

## Licensing

MIT-licensed, same as the main project - see [LICENSE](LICENSE). That's about this software; see
the main repo for how it handles the licensing of the *datasets* people analyze with it.
