MAP
  #CONFIG "PROJ_LIB" "/home/jmhicks/nca-mapgen/workspace/proj"
  NAME "NCA"
  PROJECTION
    #"init=epsg:5070"
    "init=epsg:4326"
  END
  #UNITS meters
  UNITS dd

  IMAGETYPE PNG24

  WEB
    METADATA
      ows_enable_request "*"
    END
  END

  SYMBOL
    NAME "hatch"
    TYPE hatch
  END

  $$LAYERS$$

END
  