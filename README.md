# Forge EntityModel java class Converter
 This program will convert a 1.16 Forge EntityModel class to a 1.17 EntityModel class, loosely based on a [fabric model converter by Globox_Z](https://github.com/Globox1997/ModelConverter)
# How to Use
1. Run the application downloaded from the [releases](https://github.com/Steaf23/Forge-1.17-Model-Converter/releases)
2. Select the 1.16 Java class file
3. The output 1.17 class file will be saved in the same directory as the input file
4. Be sure to back up your old files!
5. Either remove or move the old file and change the name of the file back to the original name

##Notes
- This program works best with EntityModels generated directly from blockbench (MCP mappings);
- The name of the class must be the same name as the filename (apart from teh java extension ofcourse);
- The constructor mut not have any parameters. This will prevent the program from finding the constructor at all.
- This program renames the EntityModel class parameter Entity, to the name of the file, so it's easier to use in a renderer
