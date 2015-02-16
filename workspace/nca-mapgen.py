#!/usr/bin/env python
import json, os, csv, glob, subprocess, shutil 
from itertools import product
from osgeo import ogr

##
## Functions
##
def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path);

def filename(base, dr, ext):
    return os.path.join(base, dr, '%s.%s' % (base, ext))

def get_extent(layer):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.Open(layer, 0)
    layer = data_source.GetLayer()
    extent = list(layer.GetExtent())
    # correct coordinate bbox coordinate order to conform with the rest of everything
    extent[2], extent[1] = extent[1], extent[2]
    return extent

# This funciton goes ahead and figures out all the 
# file output details in one place. Some advantages
#  1: one place handles all the string concatenation
#     etc, so methods are much more focused on the
#     business logic and have simpler method signitures
#  2: elements can be calculated in groups more simply
#     so that related things (like a boundary file and
#     the various rasters it is associated with) can
#     be grouped much more simply, even if they are
#     generated in several places
def map_output_files(base, features_dir, fields, map_template):
    output_map = {
        'dirs': {
            'base': base,
            'temp': os.path.join(base, 'temp'),
            'data': os.path.join(base, 'data'),
            'renders': os.path.join(base, 'renders')
        },
        'csv': filename(base, 'temp', 'csv'),
        'vrt': filename(base, 'temp', 'vrt'),
        'map_file': os.path.join(os.path.dirname(map_template), '%s.map' % base),
        'geo_files': {}
    }

    # build list of boundary files
    boundary_files = glob.glob('%s*.shp' % features_dir)

    for boundary_file in boundary_files:
        boundary_name = os.path.splitext(os.path.basename(boundary_file))[0]
        base_boundary_portion = '%s__%s' % (base, boundary_name)

        output_map['geo_files'][boundary_name] = {
            'boundary_file': boundary_file,
            'boundary_file_name': boundary_name,
            'points_file': os.path.join(output_map['dirs']['temp'], '%s.shp' % base_boundary_portion),
            'points_layer_name': base_boundary_portion,
            'extent': get_extent(boundary_file),
            'rasters': []
        }

        for field in fields:
            raster_layer_name = '%s__%s' % (base_boundary_portion, field['data'])
            output_map['geo_files'][boundary_name]['rasters'].append({
                'field': field['data'],
                'grid_layer_name': raster_layer_name,
                'grid_file': os.path.join(output_map['dirs']['data'], '%s.tif' % raster_layer_name),
                'render_file': os.path.join(output_map['dirs']['renders'], '%s.png' % raster_layer_name),
            })

    return output_map

## Corrects 0 to 360 longitudes to -180 to 180, writes new CSV
def write_corrected_csv(input_csv, output_csv):
    with open(input_csv, 'rb') as file_in:
        with open(output_csv, 'wt') as file_out:
            # auto-populate headers based on the first row of the CSV input
            reader = csv.DictReader(file_in, fieldnames=[], restkey='undefined-fieldnames')
            reader.fieldnames = reader.next()['undefined-fieldnames']
            writer = csv.DictWriter(file_out, fieldnames=reader.fieldnames)
            writer.writeheader()

            # iterate and correct remaining rows
            for row in reader:
                lon = float(row['LON'])
                if lon >= 180:
                    row['LON'] = lon - 360
                writer.writerow(row)

def write_vrt(base, fields, vrt_path):
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

    with open(vrt_path, 'wt') as file_out:
        file_out.write(vrt)

def extract_boundary_points(boundaries, vrt_path):
    for boundary in boundaries.values():
        subprocess.call([
            'ogr2ogr',
            '-overwrite',
            '-clipsrc',
            str(boundary['extent'][0]),
            str(boundary['extent'][1]),
            str(boundary['extent'][2]),
            str(boundary['extent'][3]),
            boundary['points_file'],
            vrt_path
        ], stdout=open(os.devnull, 'wb')) #, stderr=open(os.devnull, 'wb')

def generate_rasters(geo_files, xres, yres):
    for geo_file in geo_files:
        for raster in geo_file['rasters']:
            args = [
                'gdal_rasterize',
                '-tr',
                str(xres),
                str(yres),
                '-l',
                geo_file['points_layer_name'],
                '-a',
                raster['field'],
                geo_file['points_file'],
                raster['grid_file']
            ]
            
            subprocess.call(args) #, stdout=open(os.devnull, 'wb')

def build_mapfile(geo_files, template_map, output_map):
    mask_base = '''
  LAYER
    NAME "%s_mask"
    DATA "%s"
    STATUS OFF
    TYPE POLYGON
    CLASS
      STYLE
        COLOR 255 255 255
      END
    END
  END
'''

    layer_base =  '''
  LAYER
    NAME "%s"
    DATA "%s"
    INCLUDE "classes.cmap"
    MASK "%s_mask"
  END
'''

    layers = []
    for geo_file in geo_files:
        mask_name = geo_file['boundary_file_name']
        layers.append(mask_base % (mask_name, os.path.abspath(geo_file['boundary_file'])))
        
        for raster in geo_file['rasters']:
            layers.append(layer_base % (raster['grid_layer_name'], os.path.abspath(raster['grid_file']), mask_name))

    with open(output_map, 'wt') as file_out:
        with open(template_map, 'rb') as file_in:
            replaced = file_in.read().replace('$$LAYERS$$', ''.join(layers))
            file_out.write(replaced)

def render_images(mapfile, geo_files):
    os.putenv('REQUEST_METHOD', 'GET')
    for geo_file in geo_files:
        bbox = ','.join(map(str,geo_file['extent']))
        #bbox=str('-2235805.8,-1693186.6,2126321.7,1328674.6')
        #query_string = 'TRANSPARENT=true&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image/png&SRS=EPSG:9822&UNITS=m&WIDTH=800&HEIGHT=400&MAP=%s&LAYERS=mask,%s,states&BBOX=%s' % (mapfile, out_name, bbox)
        for raster in geo_file['rasters']:
            query_string = 'TRANSPARENT=true&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image/png&SRS=EPSG:4326&WIDTH=800&HEIGHT=400&MAP=%s&LAYERS=%s_mask,%s,states&BBOX=%s' % (mapfile, geo_file['boundary_file_name'], raster['grid_layer_name'], bbox)
            os.putenv('QUERY_STRING', query_string)

            p1 = subprocess.Popen(['./mapserv-6.4.1-CentOS-7.exe'], stdout=subprocess.PIPE)
            with open(raster['render_file'], 'w') as out:
                p2 = subprocess.Popen(['sed', '1,/^\r\{0,1\}$/d'], stdin=p1.stdout, stdout=out)

#
# Main
#
# Get properties
## TODO parameterize this from a command-line arg
config_file = open('config.json')
config = json.load(config_file)
config_file.close()

base_name = os.path.splitext(os.path.basename(config['source']['path']))[0]

# create full intended output
output_files_map = map_output_files(base_name, config['features_dir'], config['source']['fields'], config['map_template'])

# make output structure
for outdir in output_files_map['dirs'].values():
    mkdir(outdir)

# correct meridian
if config['source']['0_360']:
    write_corrected_csv(config['source']['path'], output_files_map['csv'])
else:
    shutil.copyfile(config['source']['path'], output_files_map['csv'])

# generate vrt
write_vrt(base_name, config['source']['fields'], output_files_map['vrt'])

# write out all extent shapefiles
extract_boundary_points(output_files_map['geo_files'], output_files_map['vrt'])

# create rasters for each extent shapefile
generate_rasters(output_files_map['geo_files'].values(), config['source']['xres'], config['source']['yres'])

build_mapfile(output_files_map['geo_files'].values(), config['map_template'], output_files_map['map_file'])

render_images(output_files_map['map_file'], output_files_map['geo_files'].values())

