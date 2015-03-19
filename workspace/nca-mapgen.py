#!/usr/bin/env python
import json, os, csv, glob, subprocess, shutil 
from osgeo import ogr, osr, gdal

##
## Functions
##
def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path);

def filename(base, dr, ext):
    return os.path.join(base, dr, '%s.%s' % (base, ext))

def get_extent(layer, xres, yres):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.Open(layer, 0)
    layer = data_source.GetLayer()
    extent = list(layer.GetExtent())
    # correct coordinate bbox coordinate order to conform with the rest of everything
    extent[2], extent[1] = extent[1], extent[2]
    extent = widen_extent(extent, xres, yres)
    return extent

# widens the extent by one resolution unit to make sure we
# get data that will fully encapsulate the area
def widen_extent(extent, xres, yres):
    # left-most x-coordinate
    extent[0] = extent[0] - xres
    # bottom-most y-coordinate
    extent[1] = extent[1] - yres
    # right-most x-coordinate
    extent[2] = extent[2] + xres
    # top-most y-coordinate
    extent[3] = extent[3] + yres

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
def map_output_files(base, features_dir, fields, map_template, xres, yres):
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
            'extent': get_extent(boundary_file, xres, yres),
            'rasters': []
        }

        for field in fields:
            raster_layer_name = '%s__%s' % (base_boundary_portion, field['data'])
            stat_layer_name = '%s__%s' % (base_boundary_portion, field['stat'])
            output_map['geo_files'][boundary_name]['rasters'].append({
                'field': field['data'],
                'grid_layer_name': raster_layer_name,
                'grid_file': os.path.join(output_map['dirs']['data'], '%s.tif' % raster_layer_name),
                'render_file': os.path.join(output_map['dirs']['renders'], '%s.png' % raster_layer_name),
                'interpolation_file': os.path.join(output_map['dirs']['data'], '%s_interpolation.tif' % raster_layer_name),
                'stat_field': field['stat'],
                'stat_layer_name': stat_layer_name,
                'stat_grid': os.path.join(output_map['dirs']['temp'], '%s.tif' % stat_layer_name),
                'stat_shp': os.path.join(output_map['dirs']['data'], '%s.shp' % stat_layer_name),
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
    data_template = '    <Field name="{0}" src="{0}" type="Real" />'
    stat_template = '    <Field name="{0}" src="{0}" type="String" />'
    field_arr = []

    for field in fields:
        field_arr.append(data_template.format(field['data']))
        field_arr.append(stat_template.format(field['stat']))

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
        ], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))

def generate_raster(xres, yres, points_layer, field, points_file, output):
    args = [
        'gdal_rasterize',
        '-tr',
        str(xres),
        str(yres),
        '-l',
        points_layer,
        '-a',
        field,
        points_file,
        output
    ]
            
    subprocess.call(args, stdout=open(os.devnull, 'wb'))

def generate_rasters(geo_files, xres, yres):
    for geo_file in geo_files:
        for raster in geo_file['rasters']:
            #main raster
            generate_raster(xres, 
                            yres, 
                            geo_file['points_layer_name'], 
                            raster['field'], 
                            geo_file['points_file'], 
                            raster['grid_file'])
            generate_raster(xres, 
                            yres, 
                            geo_file['points_layer_name'], 
                            raster['stat_field'][:-1], #for some reason, the shapefile conversion truncates the field name
                            geo_file['points_file'], 
                            raster['stat_grid'])

def interpolate_rasters(geo_files):
    for geo_file in geo_files:
        for raster in geo_file['rasters']:
            args = [
                'gdalwarp',
                '-overwrite',
                '-r',
                'bilinear',
                '-ts',
                '2000',
                '2000',
                '-of',
                'GTiff',
                raster['grid_file'],
                raster['interpolation_file']
            ]

            subprocess.call(args, stdout=open(os.devnull, 'wb'))

def polygonize_stats(geo_files):
    for geo_file in geo_files:
        for raster in geo_file['rasters']:
            grid = gdal.Open(raster['stat_grid'])
            band = grid.GetRasterBand(1)
            driver = ogr.GetDriverByName('ESRI Shapefile')
            if os.path.exists(raster['stat_shp']):
                driver.DeleteDataSource(raster['stat_shp'])
            outshp = driver.CreateDataSource(raster['stat_shp'])
            ref = osr.SpatialReference()
            ref.ImportFromEPSG(4326)
            outlr = outshp.CreateLayer('poly', srs = ref)
            outlr.CreateField(ogr.FieldDefn('sig', ogr.OFTInteger))
            gdal.Polygonize(band, None, outlr, 0, [], callback=None)

def build_mapfile(geo_files, template_map, output_map):
    mask_base = '''
  LAYER
    NAME "%s_mask"
    DATA "%s"
    TYPE POLYGON
    STATUS OFF
    CLASS
      STYLE
        COLOR 255 255 255
      END
    END
    PROJECTION
      "init=epsg:4326"
    END
  END
'''

    boundary_base = '''
  LAYER
    NAME "%s_boundary"
    DATA "%s"
    TYPE POLYGON
    STATUS ON
    CLASS
      STYLE
        OUTLINECOLOR 0 0 0
        WIDTH 3
        ANTIALIAS TRUE
      END
    END
    PROJECTION
      "init=epsg:4326"
    END
  END
'''

    layer_base =  '''
  LAYER
    NAME "%s"
    DATA "%s"
    STATUS ON
    TYPE RASTER
    INCLUDE "classes.cmap"
    MASK "%s_mask"
    PROJECTION
      "init=epsg:4326"
    END
  END
  LAYER
    NAME "%s"
    DATA "%s"
    TYPE POLYGON
    STATUS ON
    CLASS
      EXPRESSION ([sig] = 3)
      STYLE
        SYMBOL "hatch"
        COLOR 0 0 0
        ANGLE 45
        SIZE 8
        WIDTH 0.75
      END
    END
    CLASS
      EXPRESSION ([sig] = 2)
      STYLE
        COLOR 255 255 255
      END
    END
    MASK "%s_mask"
    PROJECTION
      "init=epsg:4326"
    END
  END
'''

    layers = []
    for geo_file in geo_files:
        mask_name = geo_file['boundary_file_name']
        layers.append(mask_base % (mask_name, os.path.abspath(geo_file['boundary_file'])))
        layers.append(boundary_base % (mask_name, os.path.abspath(geo_file['boundary_file'])))
        
        for raster in geo_file['rasters']:
            layers.append(
                layer_base % (
                    raster['grid_layer_name'],
                    os.path.abspath(raster['interpolation_file']), 
                    mask_name,
                    raster['stat_layer_name'],
                    os.path.abspath(raster['stat_shp']),
                    mask_name))

    with open(output_map, 'wt') as file_out:
        with open(template_map, 'rb') as file_in:
            replaced = file_in.read().replace('$$LAYERS$$', ''.join(layers))
            file_out.write(replaced)

def image_scale(extent, render_max):
    extent_width = extent[2] - extent[0]
    extent_height = extent[3] - extent[1]
    
    image_width = image_height = render_max
    if extent_width > extent_height:
        image_height = extent_height / extent_width * render_max
    else:
        image_width = extent_width / extent_height * render_max

    image_width_height = {
        'width': image_width, 
        'height': image_height
    }

    return image_width_height

def project_bbox(in_bbox):
    # transformation details
    in_ref = osr.SpatialReference()
    in_ref.ImportFromEPSG(4326)

    out_ref = osr.SpatialReference()
    out_ref.ImportFromEPSG(5070)
    '''
    out_ref.ImportFromWkt(
PROJCS["North_America_Albers_Equal_Area_Conic",
    GEOGCS["GCS_North_American_1983",
        DATUM["North_American_Datum_1983",
            SPHEROID["GRS_1980",6378137.0,298.257222101]],
        PRIMEM["Greenwich",0.0],
        UNIT["Degree",0.0174532925199433]],
    PROJECTION["Albers_Conic_Equal_Area"],
    PARAMETER["False_Easting",0.0],
    PARAMETER["False_Northing",0.0],
    PARAMETER["longitude_of_center",-96.0],
    PARAMETER["Standard_Parallel_1",20.0],
    PARAMETER["Standard_Parallel_2",60.0],
    PARAMETER["latitude_of_center",40.0],
    UNIT["Meter",1.0]]
)'''

    xform = osr.CoordinateTransformation(in_ref, out_ref)

    # input points to transform
    min_point = ogr.Geometry(ogr.wkbPoint)
    min_point.AddPoint(in_bbox[0], in_bbox[1])

    max_point = ogr.Geometry(ogr.wkbPoint)
    max_point.AddPoint(in_bbox[2], in_bbox[3])

    # apply transformation
    min_point.Transform(xform)
    max_point.Transform(xform)

    return [
        min_point.GetX(),
        min_point.GetY(),
        max_point.GetX(),
        max_point.GetY()
    ]

def render_images(mapfile, geo_files, render_max):
    os.putenv('REQUEST_METHOD', 'GET')
    for geo_file in geo_files:
        #projected_extent = project_bbox(geo_file['extent'])
        bbox = ','.join(map(str,geo_file['extent']))
        #bbox = ','.join(map(str,projected_extent))
        image_dimensions = image_scale(geo_file['extent'], render_max)
        for raster in geo_file['rasters']:
            query_string = ('TRANSPARENT=true&'
                            'SERVICE=WMS&'
                            'VERSION=1.1.1&'
                            'REQUEST=GetMap&'
                            'STYLES=&'
                            'FORMAT=image/png&'
                            #'SRS=epsg:5070&'
                            'SRS=epsg:4326&'
                            'WIDTH=%s&'
                            'HEIGHT=%s&'
                            'MAP=%s&'
                            'LAYERS=%s_mask,%s,%s,%s_boundary&'
                            'BBOX=%s' % (image_dimensions['width'], 
                                         image_dimensions['height'], 
                                         mapfile, 
                                         geo_file['boundary_file_name'],
                                         raster['grid_layer_name'],
                                         raster['stat_layer_name'],
                                         geo_file['boundary_file_name'],
                                         bbox))

            #
            #print query_string
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

# create full intended output listing
output_files_map = map_output_files(base_name, config['features_dir'], config['source']['fields'], config['map_template'], config['source']['xres'], config['source']['yres'])

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

interpolate_rasters(output_files_map['geo_files'].values())

polygonize_stats(output_files_map['geo_files'].values())

build_mapfile(output_files_map['geo_files'].values(), config['map_template'], output_files_map['map_file'])

render_images(output_files_map['map_file'], output_files_map['geo_files'].values(), config['render_max'])
