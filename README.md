# nca-mapgen
Scripts to help automate generating map images from model data provided by NCA

## Thoughts
The following are some thoughts on how this might be approached.

### 1: Column arg, generate VRT to wrap CSV
Assuming A2-t2m-ave.csv with data columns: P2021_2050, P2041_2070, P2070_2099

A2-t2m-ave.vrt
```xml
<OGRVRTDataSource>
  <OGRVRTLayer name="P2021_2050">
    <SrcDataSource>A2-t2m-ave.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" z="P2021_2050"/>
  </OGRVRTLayer>
  <OGRVRTLayer name="P2041_2070">
    <SrcDataSource>A2-t2m-ave.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" z="P2041_2070"/>
  </OGRVRTLayer>
  <OGRVRTLayer name="P2070_2099">
    <SrcDataSource>A2-t2m-ave.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" z="P2070_2099"/>
  </OGRVRTLayer>
</OGRVRTDataSource>
```

** Can this be streamlined?

A2-t2m-ave.vrt
```xml
<OGRVRTDataSource>
  <SrcDataSource>A2-t2m-ave.csv</SrcDataSource>
  <OGRVRTLayer name="P2021_2050">
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" z="P2021_2050"/>
  </OGRVRTLayer>
  <OGRVRTLayer name="P2041_2070">
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" z="P2041_2070"/>
  </OGRVRTLayer>
  <OGRVRTLayer name="P2070_2099">
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>WGS84</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="LON" y="LAT" z="P2070_2099"/>
  </OGRVRTLayer>
</OGRVRTDataSource>
```

### 2: gdal_rasterize on each layer of the VRT

gdal_rasterize -a z -l P2021_2050 A2-t2m-ave.vrt A2-t2m-ave__P2021_2050.tif

-> this may require the [-tr xres yres] bit to make the grid work correctly

This should create a global raster for the data.

### 3: Sty

