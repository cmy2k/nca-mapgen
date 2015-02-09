import json, os, csv

##
## Functions
##
def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path);

def correct_meridian(base, path):
    output_path = '{0}/temp/{0}.csv'.format(base)

    # TODO auto populate fieldnames
    fields = ['Zonal_Dir','LON','Merdian_Dir','LAT','P2021_2050','Stat_sig_50','P2041_2070','Stat_sig_70','P2070_2099','Stat_sig_99']
    with open(output_path, 'wt') as file_out:
        with open(path, 'rb') as file_in:
            reader = csv.DictReader(file_in, fieldnames=fields)
            writer = csv.DictWriter(file_out, fieldnames=fields)
            writer.writeheader()
            reader.next()
            for row in reader:
                lon = float(row['LON'])
                if lon >= 180:
                    row['LON'] = lon - 360
                writer.writerow(row)

def format_vrt(base, fields):
    field_template = '<Field name="{0}" src="{0}" type="Real" />'
    field_arr = []

    for field in fields:
        field_arr.append(field_template.format(field['data']))

    vrt = '''
<OGRVRTDataSource>
  <OGRVRTLayer name="%s">
    <SrcDataSource relativeToVRT="1">%s.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" />
    %s
  </OGRVRTLayer>
</OGRVRTDataSource>
''' % (base, csv, '\n'.join(field_arr))

    output_path = '{0}/temp/{0}.vrt'.format(base)
    with open(output_path, 'wt') as file_out:
        file_out.write(vrt)

#
# Main
#
# Get properties
## TODO parameterize this from a command-line arg
config_file = open('config.json')
config = json.load(config_file)
config_file.close()

# make output structure
base = os.path.splitext(config['source']['path'])[0]
temp_dir = os.path.join(base, 'temp')
data_dir = os.path.join(base, 'data')
renders_dir = os.path.join(base, 'renders')

mkdir(base)
mkdir(temp_dir)
mkdir(data_dir)
mkdir(renders_dir)

# correct meridian
if config['source']['0_360']:
    correct_meridian(base, config['source']['path'])

# generate vrt
format_vrt(base, config['source']['fields'])
