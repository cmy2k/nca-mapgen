import json, os, csv, glob, subprocess
from osgeo import ogr

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

def write_vrt(base, fields):
    field_template = '    <Field name="{0}" src="{0}" type="Real" />'
    field_arr = []

    for field in fields:
        field_arr.append(field_template.format(field['data']))

    vrt = '''
<OGRVRTDataSource>
  <OGRVRTLayer name="{0}">
    <SrcDataSource relativeToVRT="1">{0}.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" />
{1}
  </OGRVRTLayer>
</OGRVRTDataSource>
'''.format(base, '\n'.join(field_arr))

    output_path = '{0}/temp/{0}.vrt'.format(base)
    with open(output_path, 'wt') as file_out:
        file_out.write(vrt)

    return output_path

def extract_extents(features_dir, vrt_path):
    outfiles = []
    features_files = glob.glob('%s*.shp' % features_dir)
    driver = ogr.GetDriverByName('ESRI Shapefile')
    for features_file in features_files:
        data_source = driver.Open(features_file, 0)
        layer = data_source.GetLayer()
        extent = layer.GetExtent()

        print extent

        fportion = os.path.splitext(os.path.basename(features_file))[0]
        out_file = '%s__%s.shp' % (os.path.splitext(vrt_path)[0], fportion)
        outfiles.append(out_file)

        subprocess.call([
            'ogr2ogr',
            '-overwrite',
            '-clipsrc',
            str(extent[0]),
            str(extent[2]),
            str(extent[1]),
            str(extent[3]),
            out_file,
            vrt_path
        ])

    return outfiles

def generate_rasters(base, outfiles, fields, xres, yres):
    output_base = '%s/data/' % base
    for outfile in outfiles:
        out_name = os.path.splitext(os.path.basename(outfile))[0]
        for field in fields:
            out_file = '%s%s__%s.tif' % (output_base, out_name, field['data'])
            args = [
                'gdal_rasterize',
                '-tr',
                str(xres),
                str(yres),
                '-l',
                out_name,
                '-a',
                field['data'],
                outfile,
                out_file
            ]
            
            subprocess.call(args)

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
vrt_path = write_vrt(base, config['source']['fields'])

# write out all extent shapefiles
outfiles = extract_extents(config['features_dir'], vrt_path)

# create rasters for each extent shapefile
generate_rasters(base, outfiles, config['source']['fields'], config['source']['xres'], config['source']['yres'])
