# nca-mapgen
Scripts to help automate generating map images from model data provided by NCA

## Thoughts
The following are some thoughts on how this might be approached.

Arguments:
- Input CSV
- List of raster columns
- List of stats columns
- Pixel resolution
- Path to directory of clip shapes
- Mapfile path (can contain references to other map elements)

Example input:
- A2-t2m-ave.csv
- P2021_2050,P2041_2070,P2070_2099
- Stat_sig_50,Stat_sig_70,Stat_sig_99
- 2.8
- clips/
-- conus.shp
-- hi.shp
-- hi_buffer.shp
-- ak.shp
-- ak_buffer.shp
- A2-t2m-ave.map.tpl

Output:
A2-t2m-ave/

__ P2021_2050/ 
____ data/ 
______ A2-t2m-ave__P2021_2050.tif 
______ A2-t2m-ave__P2021_2050__conus.tif 
______ A2-t2m-ave__P2021_2050__hi.tif 
______ A2-t2m-ave__P2021_2050__hi_buffer.tif 
______ A2-t2m-ave__P2021_2050__ak.tif 
______ A2-t2m-ave__P2021_2050__ak_buffer.tif 
____ renders/ 
______ A2-t2m-ave__P2021_2050__conus.png 
______ A2-t2m-ave__P2021_2050__hi.png 
______ A2-t2m-ave__P2021_2050__hi_buffer.png 
______ A2-t2m-ave__P2021_2050__ak.png 
______ A2-t2m-ave__P2021_2050__ak_buffer.png 
__ P2041_2070/ 
____ data/ 
______ A2-t2m-ave__P2041_2070.tif 
______ A2-t2m-ave__P2041_2070__conus.tif 
______ A2-t2m-ave__P2041_2070__hi.tif 
______ A2-t2m-ave__P2041_2070__hi_buffer.tif 
______ A2-t2m-ave__P2041_2070__ak.tif 
______ A2-t2m-ave__P2041_2070__ak_buffer.tif 
____ renders/ 
______ A2-t2m-ave__P2041_2070__conus.png 
______ A2-t2m-ave__P2041_2070__hi.png 
______ A2-t2m-ave__P2041_2070__hi_bu7fer.png 
______ A2-t2m-ave__P2041_2070__ak.png 
______ A2-t2m-ave__P2041_2070__ak_buffer.png 

__ P2070_2099/ 
____ data/ 
______ A2-t2m-ave__P2070_2099.tif 
______ A2-t2m-ave__P2070_2099__conus.tif 
______ A2-t2m-ave__P2070_2099__hi.tif 
______ A2-t2m-ave__P2070_2099__hi_buffer.tif 
______ A2-t2m-ave__P2070_2099__ak.tif 
______ A2-t2m-ave__P2070_2099__ak_buffer.tif 
____ renders/ 
______ A2-t2m-ave__P2070_2099__conus.png 
______ A2-t2m-ave__P2070_2099__hi.png 
______ A2-t2m-ave__P2070_2099__hi_buffer.png 
______ A2-t2m-ave__P2070_2099__ak.png 
______ A2-t2m-ave__P2070_2099__ak_buffer.png 

### 1: Subtract 180 from all longitudes
The source data has longitudes ranging from 0 to 360. It is more common for WGS84 data to be presented in a range of -180 to 180. To make processing easier later, all rows are looped over, and each longitude value is subtracted by 180.

### 2: Column arg, generate VRT to wrap CSV
Assuming A2-t2m-ave.csv with data columns: P2021_2050, P2041_2070, P2070_2099

A2-t2m-ave.vrt
```xml
<OGRVRTDataSource>
  <OGRVRTLayer name="A2-t2m-ave">
    <SrcDataSource relativeToVRT="1">A2-t2m-ave.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" />
    <Field name="P2021_2050" src="P2021_2050" type="Real" />
    <Field name="P2041_2070" src="P2041_2070" type="Real" />
    <Field name="P2070_2099" src="P2070_2099" type="Real" />
  </OGRVRTLayer>
</OGRVRTDataSource>
```

### 3: gdal_rasterize on each layer of the VRT

gdal_rasterize -tr 2.8 2.8 -l A2-t2m-ave -a P2021_2050 A2-t2m-ave.vrt A2-t2m-ave__P2021_2050.tif

This creates an unstyled global raster

### 4: wrap raster around Prime Meridian
The input data set has longitudes ranging from 0-360, but -180-180 are more typical. As such, the raster is processed with the following step:

gdalwarp -t_srs WGS84 /Users/cmy2k/Documents/src/nemac/nca/foo.tif /Users/cmy2k/Documents/src/nemac/nca/foo2.tif -wo SOURCE_EXTRA=1000 --config CENTER_LONG 0

### 3: Clip out global raster

