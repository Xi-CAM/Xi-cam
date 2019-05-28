# Configuration file for bluesky-browser

## SEARCH RESULTS
#
# This is the default function that populates the list of search results,
# provided in full here as an example.
#
#from datetime import datetime
#
#def search_result_row(entry):
#    "Take in an entry and return a dict mapping column names to values."
#    start = entry.metadata['start']
#    stop = entry.metadata['stop']
#    start_time = datetime.fromtimestamp(start['time'])
#    duration = datetime.fromtimestamp(stop['time']) - start_time
#    if stop is None:
#        str_duration = '-'
#    else:
#        duration = datetime.fromtimestamp(stop['time']) - start_time
#        str_duration = str(duration)
#        str_duration = str_duration[:str_duration.index('.')]
#    return {'Unique ID': start['uid'][:8],
#            'Transient Scan ID': str(start.get('scan_id', '-')),
#            'Plan Name': start.get('plan_name', '-'),
#            'Start Time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
#            'Duration': str_duration,
#            'Exit Status': '-' if stop is None else stop['exit_status']}
#
#c.SearchState.search_result_row = search_result_row
#
## VIEWER
#
#from bluesky_browser.viewer.header_tree import HeaderTreeFactory
#from bluesky_browser.viewer.baseline import BaselineFactory
#from bluesky_browser.viewer.figures import FigureManager, LinePlotManager
#
#c.RunViewer.factories = [
#    HeaderTreeFactory,
#    BaselineFactory,
#    FigureManager,
#]
#
## VISUALIZATION
#
#c.FigureManager.factories = [LinePlotManager]
#
#c.LinePlotManager.omit_single_point_plot = True
#c.FigureManager.enabled = True
#c.FigureManager.exclude_streams = set()
