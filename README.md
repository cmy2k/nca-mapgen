# nca-mapgen
Scripts to help automate generating map images from model data provided by NCA

## Prerequisites
- gdal/ogr
- gdal/ogr python bindings

## Usage
Expects the following arrangement within a directory:
- nca-mapgen.py
- input.csv
- boundaries_dir/
- config.json

See workspace/config.json for example config. The elements are as follows:
- source: object of attributes describing the input CSV
  - path: relative path to csv file
  - xres: x-axis resolution to be used during rasterizing
  - yres: y-axis resolution to be used during rasterizing
  - 0_360: boolean to indicate if the input dataset spans from 0 to 360 instead of -180 to 180 as is typical for WGS84. If true, the input values with longitudes of 180 or more will be subtracted by 360. This moves the values to the west of the Prime Meridian and corrects the dataset to be within the range of -180 to 180.
  - fields: this is an array of data/stat pairs to describe the CSV attribute columns that should be turned into new datasets. Each is an object that follows this pattern:
    - data: column name a data column. This will be the basis of one of the boundary rasters.
    - stat: the statistical significance column that will be used as an overlay in the map composition. This needs to be paired with the data column so that it's clear what stat column goes with what data column in the output map composition.

- features_dir: path to all the boundary shapefiles. The extent of each will be used as the basis for an output raster. The features can be multipart - the full extent of all data within will be used for CSV datapoint extraction.
- map_template: base template for styling the map compositions.
    

To run (assuming *nix with chmod +x):
```
./nca-mapgen.py
```

Otherwise:  
```
python nca-mapgen.py
```

## Outputs
A new dir will be created relative to the script location. It will take the base name of the input.csv. Additionally, the script will generate files for every permutation of boundaries and attributes. So for example:

input.csv has:  
- attribute-a
- attribute-b

and in boundaries_dir/  
- boundary-1.shp
- boundary-2.shp

outputs will be generated as such:
- input__boundary-1__attribute-a
- input__boundary-1__attribute-b
- input__boundary-2__attribute-a
- input__boundary-2__attribute-b

The output is arranged into several subdirectories within the output dir. They include:
- data: this is where the generated rasters go for each CSV attribute/boundary permutation
- renders: this is where the actual map composition images are output
- temp: inclues several intermediate vector products to help generate the rasters

## TODO
### Features
- How to handle significance?
- Render map compositions

### Enhancements
- actually follow some practices in the code / modularize :]
- auto-populate fieldnames in CSV parsing
- parameterize path to config.json as a command-line arg

- - -

## Development notes
The following are some thoughts on how this might be approached.

Arguments:
- Input CSV
- List of raster columns
- List of stats columns
- Pixel resolution X,Y
- Path to directory of clip shapes
- Mapfile path (can contain references to other map elements)

Example input:
- config.json
- A2-t2m-ave.csv
- boundaries/  
  - conus.shp
  - hi.shp
  - ak.shp

Output:
A2-t2m-ave/  

__ temp/  
____ A2-t2m-ave_180.csv  
____ A2-t2m-ave.vrt  
____ A2-t2m-ave__conus.shp  
____ A2-t2m-ave__hi.shp  
____ A2-t2m-ave__ak.shp  

__ data/  
____ A2-t2m-ave__P2021_2050__conus.tif  
____ A2-t2m-ave__P2021_2050__hi.tif  
____ A2-t2m-ave__P2021_2050__ak.tif  
____ A2-t2m-ave__P2041_2070__conus.tif  
____ A2-t2m-ave__P2041_2070__hi.tif  
____ A2-t2m-ave__P2041_2070__ak.tif  
____ A2-t2m-ave__P2070_2099__conus.tif  
____ A2-t2m-ave__P2070_2099__hi.tif  
____ A2-t2m-ave__P2070_2099__ak.tif  

__ renders/  
____ A2-t2m-ave__P2021_2050__conus.png  
____ A2-t2m-ave__P2021_2050__hi.png  
____ A2-t2m-ave__P2021_2050__ak.png  
____ A2-t2m-ave__P2041_2070__conus.png  
____ A2-t2m-ave__P2041_2070__hi.png  
____ A2-t2m-ave__P2041_2070__ak.png  
____ A2-t2m-ave__P2070_2099__conus.png  
____ A2-t2m-ave__P2070_2099__hi.png  
____ A2-t2m-ave__P2070_2099__ak.png  

Note:  
Generally, the process of rasterize, then clip, is that there's some odd things that happen to the outputs. They don't quite line up with the original, and this is potentially very problematic with the data representation.

### 0 (if necessary): Correct Prime Meridian arrangement
The source data has longitudes ranging from 0 to 360. It is more common for WGS84 data to be presented in a range of -180 to 180. Rows past 180 are subtracted by 360 to wrap them to the other side of the prime meridian.

### 1: Column arg, generate VRT to wrap CSV
Assuming A2-t2m-ave.csv (or derived from step 0: A2-t2m-ave.csv) with data columns: P2021_2050, P2041_2070, P2070_2099

A2-t2m-ave.vrt
```xml
<OGRVRTDataSource>
  <OGRVRTLayer name="A2-t2m-ave">
    <SrcDataSource relativeToVRT="1">A2-t2m-ave_180.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" />
    <Field name="P2021_2050" src="P2021_2050" type="Real" />
    <Field name="P2041_2070" src="P2041_2070" type="Real" />
    <Field name="P2070_2099" src="P2070_2099" type="Real" />
  </OGRVRTLayer>
</OGRVRTDataSource>
```

### 3: Find extent of each clip boundary
Attempting to clip the vrt using ogr2ogr -clipsrc with a shapefile specified is _very_ slow. I think a better procedure will be to get general boxes for the features, then clip to those. This is incredibly faster, plus it gives some spillover around the shape which is desirable.

Do this for every clip:
```
ogrinfo -so input/boundaries/conus.shp conus | grep "Extent: "
-->> Extent: (-124.848974, 24.396308) - (-66.885444, 49.384358)
```

Then:
```
ogr2ogr -clipsrc -124.848974 24.396308 -66.885444 49.384358  A2-t2m-ave/temp/A2-t2m-ave__conus.shp A2-t2m-ave/temp/A2-t2m-ave.vrt
```

### 4: gdal_rasterize on each column of each extent shapefile
gdal_rasterize -tr 2.8125 2.79 -l A2-t2m-ave__conus -a P2021_2050 A2-t2m-ave/temp/A2-t2m-ave__conus.shp A2-t2m-ave/data/A2-t2m-ave__P2021_2050__conus.tif

This creates unstyled rasters for each extent and attribute combination.

