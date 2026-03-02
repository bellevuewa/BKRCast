rem daysim\daysim -c daysim\daysim_configuration.properties
python scripts/summarize/standard/tour_mode_share_calculator.py
python scripts/summarize/standard/tour_mode_share_calculator.py Bellevue
python scripts/summarize/standard/tour_mode_share_calculator.py BelDT
python scripts/summarize/standard/tour_mode_share_calculator.py -s "F:\projects\2024baseyear\BKR3-24-v37_telecommute\inputs\subarea_definition\BKR_only_TAZ.txt"
python scripts/summarize/standard/trip_mode_share_calculator.py
python scripts/summarize/standard/trip_mode_share_calculator.py Bellevue
python scripts/summarize/standard/trip_mode_share_calculator.py BelDT
python scripts/summarize/standard/trip_mode_share_calculator.py -s "F:\projects\2024baseyear\BKR3-24-v37_telecommute\inputs\subarea_definition\BKR_only_TAZ.txt"
python scripts/summarize/standard/telecommute_analysis.py