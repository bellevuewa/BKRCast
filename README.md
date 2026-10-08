# BKRCast

The BKR ([Bellevue](http://www.ci.bellevue.wa.us/), [Kirkland](http://www.kirklandwa.gov/), [Redmond](http://www.redmond.gov/)) Travel Demand Model.  Fore more information, see the [documentation](https://github.com/Bellevuewa/BKRCast/wiki). 

The project root is resolved from `input_configuration.py`, so moving a checkout
does not require editing `project_folder`. Launch `run_bkrcast.py` by its full
path from any directory; the runner sets its working directory to the checkout
before starting model stages.

Copy `local_configuration_template.ini` to `local_configuration.ini` beside
`input_configuration.py`, then set `paths.parcels_file_folder` to your parcel
source directory. Set `paths.daysim_code` to the executable source directory;
relative paths are resolved from the checkout directory. Configure years,
scenario name, and modeller initials in `[scenario]`, and all boolean settings
in `[flags]`. Boolean values accept `true/false`, `yes/no`, `on/off`, or `1/0`.
`local_configuration.ini` is ignored by Git; the template is versioned. Missing
required settings, empty path/scenario settings, and invalid boolean values
raise configuration errors.

Other model parameters remain in `input_configuration.py`. Directly launched
legacy model scripts may still require the checkout as their working directory.
