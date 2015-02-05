# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------------
# Script for calculating Least Cost Path between two points in ArcGIS python
# 
# Copyright (c) 2015 Jiri Kadlec and Zhi Li
#
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to deal 
# in the Software without restriction, including without limitation the rights to 
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
# of the Software, and to permit persons to whom the Software is furnished to do so, 
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS 
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
# 
# --------------------------------------------------------------------------------------
#
# usage of this script from commandline:
# C:\python27\ArcGIS10.2\python.exe leastcost.py data_folder output_name 1 1 1 1 1 1
#
# where 1 1 1 1 1 1 are the cost weights for road, rail, river, lake, slope and elevation,
# data_folder is the full path to the folder with input data, and output_name is the short
# name of the output (result) data folder. The output will be created as a subfolder inside
# data_folder by the script. The script will also create a file map.pdf showing map of the
# least-cost path.
#

import arcpy
import os
import sys

##############################################################################
# This function makes the buffer, converts it to raster, and reclassifies it.
# it is used for preparing rasters for road, railroad, river and lake for the 
# cost raster
##############################################################################
def create_cost_layer(folder, dem_raster, shapefile, out_raster_file, buffer_m):
    #setup folder for temporary results

    #get cellsize and spatial reference for new raster
    sp = dem_raster.spatialReference
    cellSize = dem_raster.meanCellWidth

    #reproject it to same projection as dem
    vectorFile = os.path.join(folder, shapefile)
    vectorFileProj = os.path.join(temp, "projected_" + shapefile)
    arcpy.Project_management(vectorFile, vectorFileProj, sp)

    #get buffer
    bufferFile = os.path.join(temp, "buffer_" + shapefile)
    arcpy.Buffer_analysis(vectorFileProj, bufferFile, str(buffer_m) + " meters")
    arcpy.AddMessage("buffer done!")

    #feature to raster
    rasterFile = os.path.join(temp, "raster_" + shapefile.strip(".shp") + ".tif")
    arcpy.FeatureToRaster_conversion(bufferFile,"BUFF_DIST",rasterFile, cellSize)
    arcpy.AddMessage("feature to raster done!")

    #reclassify to a raster with [0, 1]
    raster = arcpy.sa.Raster(rasterFile)
    cost_raster = arcpy.sa.Con(arcpy.sa.IsNull(raster), 0, 1)
    costFile1 = os.path.join(temp, out_raster_file)
    cost_raster.save(costFile1)
    arcpy.AddMessage("reclassify " + shapefile + " done!")

##################################################################
# Function to calculate cost layers for elevation and for slope
##################################################################
def create_cost_layer_dem(folder, dem_raster, slopeCostFile, elevCostFile):
    #get and reclassify the slope
    slopefile1 = os.path.join(temp, slopeCostFile)
    slope = arcpy.sa.Slope(dem_raster, "PERCENT_RISE", "0.1")
    slope.save(slopefile1)
    arcpy.AddMessage("slope: done!")

    #reclassify the DEM raster
    min = dem_raster.minimum
    max = dem_raster.maximum
    arcpy.AddMessage("DEM statistics: min:" + str(min) + " max: " + str(max))
    demRas2 = dem_raster - min
    demRas3 = (demRas2) * (10.0 / max)
    demfile1 = os.path.join(temp, elevCostFile)
    demRas3.save(demfile1)

##################################################################
# Function to Prepare the input data and create the cost layers
##################################################################
def prepare_data(folder, dem, rail, road, river, lake):
    #create folder for temporary files
    try:
        os.makedirs(temp)
    except OSError:
        pass

    #initialize geoprocessing setting to same cellsize and same
    #extent as the DEM raster
    demfile = os.path.join(folder, dem)
    arcpy.CalculateStatistics_management(demfile)
    dem_raster = arcpy.sa.Raster(demfile)
    arcpy.AddMessage("DEM file:" + demfile)
    arcpy.env.extent = dem_raster.extent
    arcpy.env.snapRaster = dem_raster

    slopeCost = "cost_slope.tif"
    elevCost = "cost_elev.tif"
    create_cost_layer_dem(folder, dem_raster, slopeCost, elevCost)

    roadCost = "cost_road.tif"
    create_cost_layer(folder, dem_raster, road, roadCost, 2000)

    railCost = "cost_rail.tif"
    create_cost_layer(folder, dem_raster, rail, railCost, 2000)

    lakeCost = "cost_lake.tif"
    create_cost_layer(folder, dem_raster, lake, lakeCost, 2000)

    riverCost = "cost_river.tif"
    create_cost_layer(folder, dem_raster, river, riverCost, 2000)


##################################################################
# Function to Add least cost path layer to the map
##################################################################
def add_path_to_map(mxd, leastCostPath):

    pathLayer = None
    for lyr in arcpy.mapping.ListLayers(mxd):
        if lyr.name == "least_cost_path":
            pathLayer = lyr

    if pathLayer is not None:
        arcpy.mapping.RemoveLayer(mxd.activeDataFrame, pathLayer)

    newPathLayer = arcpy.mapping.Layer(leastCostPath)
    pathSymbol = arcpy.mapping.Layer(os.path.join(folder, symbol))
    arcpy.mapping.AddLayer(mxd.activeDataFrame, newPathLayer)
    for lyr in arcpy.mapping.ListLayers(mxd):
        if lyr.name == "least_cost_path":
            arcpy.mapping.UpdateLayer(mxd.activeDataFrame, lyr, pathSymbol)

    arcpy.RefreshActiveView()


##################################################################
# Start of main script !                                         #
##################################################################

print 'Number of arguments:', len(sys.argv), 'arguments.'
print sys.argv

# Check out any necessary licenses
arcpy.CheckOutExtension("spatial")
# Find what is our folder
folder = sys.argv[1]
#folder = arcpy.GetParameterAsText(0)
arcpy.AddMessage("folder:" + folder)

# Find the weights from the user
outputFolderName = sys.argv[2]
roadWeight = int(sys.argv[3])
railWeight = int(sys.argv[4])
lakeWeight = int(sys.argv[5])
riverWeight = int(sys.argv[6])
slopeWeight = int(sys.argv[7])
elevWeight = int(sys.argv[8])

# Define Global Variable for Output Folder
global temp

temp = os.path.join(folder, outputFolderName)
arcpy.AddMessage("output folder:" + temp)

# Get our input files
arcpy.env.overwriteOutput = True

dem = "dem.tif"
SLC = "start.shp"
LV = "finish.shp"
rail = "railroads.shp"
lake = "lakes.shp"
river = "rivers.shp"
road = "roads.shp"

symbol = "leastcost.lyr"

prepare_data(folder, dem, rail, road, river, lake)
arcpy.AddMessage("Prepare data completed!")

#now construct the cost raster!
#multipliers for each factor are entered by our users
slopeCostFile = os.path.join(temp, "cost_slope.tif")
lakeCostFile = os.path.join(temp, "cost_lake.tif")
riverCostFile = os.path.join(temp, "cost_river.tif")
railCostFile = os.path.join(temp, "cost_rail.tif")
roadCostFile = os.path.join(temp, "cost_road.tif")
elevCostFile = os.path.join(temp, "cost_elev.tif")

cost_raster = (arcpy.sa.Raster(slopeCostFile) * slopeWeight +
               arcpy.sa.Raster(lakeCostFile) * lakeWeight +
               arcpy.sa.Raster(riverCostFile) * riverWeight +
               arcpy.sa.Raster(railCostFile) * railWeight +
               arcpy.sa.Raster(roadCostFile) * roadWeight +
               arcpy.sa.Raster(elevCostFile) * elevWeight)
cost_raster_file = os.path.join(temp, "cost_raster.tif")
cost_raster.save(cost_raster_file)
arcpy.AddMessage("cost raster: done!")

#now do the cost distance
backlinkFile = os.path.join(temp, "backlink.tif")

SLC = os.path.join(folder, SLC)
distance_raster = arcpy.sa.CostDistance(SLC, cost_raster_file, 200000000,backlinkFile)
distance_raster.save(os.path.join(temp, "distance_raster.tif"))
arcpy.AddMessage("cost distance raster: done!")

#now get the path
LV = os.path.join(folder, LV)
path_raster = arcpy.sa.CostPath(LV, distance_raster, backlinkFile)
path_raster.save(os.path.join(temp, "path_raster.tif"))
arcpy.AddMessage("cost path raster: done!")

#now convert the path to polyline
leastCostPath = os.path.join(temp, "least_cost_path.shp")
arcpy.RasterToPolyline_conversion(path_raster, leastCostPath)
arcpy.AddMessage("least cost path: done!")

#update the path displayed in the current map document
mxd = arcpy.mapping.MapDocument(os.path.join(folder, "leastcost.mxd"))

add_path_to_map(mxd, leastCostPath)

#update the weights label and the title
for e in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
    if e.name == "txtWeights":
        e.text = "Elevation: %s Slope: %s Road: %s Rail: %s River: %s Lake: %s" \
                 % (elevWeight, slopeWeight, roadWeight, railWeight, riverWeight, lakeWeight)
    if e.name == "txtTitle":
        e.text = "SLC to LV Railroad: " + outputFolderName

#export map to pdf!
pdfFile = os.path.join(temp, "map.pdf")
arcpy.mapping.ExportToPDF(mxd, pdfFile)
arcpy.AddMessage("Final map saved to: " + pdfFile)