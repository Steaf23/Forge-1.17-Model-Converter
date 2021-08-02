# All library stuff
import tkinter as tk
from tkinter import messagebox as mb
from tkinter.filedialog import askopenfilename
import re
import os
from typing import List, AnyStr, Tuple


def open_file():
    path = askopenfilename(title="Select Forge 1.16 EntityModel .java class")

    if path == "":
        root.destroy()
        return
    file = open(path)

    file_lines = file.readlines()
    file.close()

    file_lines.insert(0, "// Forge model conversion from 1.16 to 1.17 by Steven (Steaf23), program outline loosely "
                         "based on https://github.com/Globox1997/ModelConverter\n")
    file_lines.insert(1, "// Generate all required imports yourself\n")

    # Initialize model parts
    replace_model_renderer(file_lines)

    # get texture size
    texture_size = get_and_remove_texture_size(file_lines)

    # replace constructor and return cube parts for later
    class_name, _extension = os.path.basename(path).split(".")
    parts, ending_index = convert_constructor(class_name, file_lines)

    file_lines = remove_after_line(ending_index, file_lines)

    add_layer_definition(parts, ending_index, file_lines, texture_size)
    add_anim_and_render(file_lines, parts)

    # Filter empty elements
    file_lines = list(filter(lambda item: item != rem_line, file_lines))

    newfile = open(path.replace(".java", "") + "Converted.java", "w")
    newfile.writelines(file_lines)
    newfile.close()

    root.destroy()


def replace_model_renderer(file_lines: List[AnyStr]) -> None:
    # look for ModelRenderers
    found_model_init: bool = False
    for i, renderer_string in enumerate(file_lines):
        if "final ModelRenderer" in renderer_string:
            file_lines[i] = renderer_string.replace("ModelRenderer", "ModelPart")
            found_model_init = True
        elif found_model_init:
            break


def get_and_remove_texture_size(file_lines: List[AnyStr]) -> List[int]:
    texture_size = []
    for texture_string in file_lines:
        if "setTextureSize" in texture_string:
            texture_size.append(int(re.search(r'\d+', texture_string).group()))
            texture_size.append(texture_size[0])
            break
        else:
            # check for blockbenchlike texture size
            if "textureWidth" in texture_string:
                texture_size.append(get_numbers(texture_string)[0])
                next_line = file_lines[file_lines.index(texture_string) + 1]
                if "textureHeight" in next_line:
                    texture_size.append(get_numbers(next_line)[0])
                else:
                    texture_size.append(texture_size[0])
                if file_lines[file_lines.index(texture_string) + 2] == "\n":
                    file_lines[file_lines.index(texture_string) + 2] = rem_line
                file_lines[file_lines.index(texture_string) + 1] = rem_line
                file_lines[file_lines.index(texture_string)] = rem_line
                break
    return texture_size


def convert_constructor(class_name: AnyStr, file_lines: List[AnyStr]) -> Tuple[List[dict], int]:
    constructor_found = False

    for line_index, line in enumerate(file_lines):
        if (class_name + "()") in line:
            file_lines[line_index] = file_lines[line_index].replace(class_name + "()", class_name + "(ModelPart model)")
            constructor_found = True

        if constructor_found:
            ending_index = 0

            parts = build_part_list(file_lines)
            deleted = False
            add_i = 1
            while not deleted:
                final_index = line_index + add_i
                line = file_lines[final_index]
                if "}" in line:
                    ending_index = file_lines.index(line) + len(parts) + 1
                    add_new_constructor(final_index - 1, file_lines, parts)
                    break
                file_lines[final_index] = rem_line
                add_i += 1

            return parts, ending_index
    else:
        print("Couldn't find main method")
        mb.showerror(title=None, message="Error: Constructor not found!\n"
                                         "File name has to be the same as the class name!\n"
                                         "No constructor overloading!\n"
                                         "No constructor parameters!\n")
        root.destroy()
        exit(-1)
        return [], -1


def build_part_list(file_lines) -> List[dict]:
    parts: List = []
    for i, line in enumerate(file_lines):
        if "new ModelRenderer(this)" in line:
            field_name = get_field_name(line)
            part: dict = {"name": field_name,
                          "id_name": field_name.lower()}
            part_i = 1
            cubes = []
            while line != "\n":
                line = file_lines[i + part_i]
                if "setRotationPoint" in line:
                    part["pivot"] = get_numbers(line)
                if "addChild" in line:
                    part["parent"] = get_field_name(line)
                if "setRotationAngle" in line:
                    part["rotation"] = get_numbers(line)
                if "setTextureOffset" in line:
                    f = get_numbers(line)
                    cube: dict = {"uv_position": [f[0], f[1]],
                                  "origin": [f[2], f[3], f[4]],
                                  "size": [f[5], f[6], f[7]],
                                  "inflate": f[8],
                                  "mirrored": get_booleans(line)[0]}
                    cubes.append(cube)
                    part["cubes"] = cubes
                if "rotation" not in part:
                    part["rotation"] = [0.0, 0.0, 0.0]
                part_i += 1
            parts.append(part)
    return parts


def add_new_constructor(starting_index: int, file_lines: List[AnyStr], parts: List[dict]) -> None:
    for i, part in enumerate(parts):
        assignment_string = "\t\tthis." + part["name"] + " = "
        if "parent" in part:
            # if the part has a grandparent
            if "parent" in get_part_by_name(part["parent"], parts):
                parent = "this." + part["parent"]
            else:
                parent = "model"
            assignment_string += '%s.getChild("%s");' % (parent, part["id_name"])
        else:
            assignment_string += "model;"

        file_lines.insert(starting_index + i, assignment_string + "\n")
        i += 1


def add_layer_definition(parts: List[dict], starting_index: int, file_lines: List[AnyStr],
                         texture_size: List[int]) -> None:
    line_index = starting_index
    file_lines.append("\n"
                      "\tpublic static LayerDefinition createBodyLayer() {\n"
                      "\t\tMeshDefinition meshDefinition = new MeshDefinition();\n"
                      "\t\tPartDefinition partDefinition = meshDefinition.getRoot();\n")

    line_index += 1
    for part in parts:
        file_lines.append('\n\t\tpartDefinition.addOrReplaceChild("%s", CubeListBuilder.create()' % part["id_name"])
        for cube in part["cubes"]:
            tex_offs_string = "\n\t\t\t\t\t\t.texOffs(%d, %d)" % (cube["uv_position"][0],
                                                                  cube["uv_position"][1])
            box_string = ".addBox(%sf, %sf, %sf, %sf, %sf, %sf" % (cube["origin"][0],
                                                                   cube["origin"][1],
                                                                   cube["origin"][2],
                                                                   cube["size"][0],
                                                                   cube["size"][1],
                                                                   cube["size"][2])
            inflate_string = ", new CubeDeformation(%.2ff))" % (cube["inflate"]) if cube["inflate"] != 0.0 else ")"
            mirror_string = ".mirror()" if cube["mirrored"] else ""
            cube_string = tex_offs_string + box_string + inflate_string + mirror_string + ","
            file_lines.append(cube_string)

        pose_string = "\n\t\t\t\tPartPose.offsetAndRotation" \
                      "(%sf, %sf, %sf, %sf, %sf, %sf));\n" % (part["pivot"][0],
                                                              part["pivot"][1],
                                                              part["pivot"][2],
                                                              part["rotation"][0],
                                                              part["rotation"][1],
                                                              part["rotation"][2],)

        file_lines.append(pose_string)

    file_lines.append("\n\t\treturn LayerDefinition.create(meshDefinition, %s, %s);\n\t}\n" % (str(texture_size[0]),
                                                                                               str(texture_size[1])))


def add_anim_and_render(file_lines: List[AnyStr], parts: List[dict]) -> None:
    file_lines.append("\n\t@Override"
                      "\n\tpublic void setupAnim(Entity entityIn, float limbSwing, float limbSwingAmount, "
                      "float ageInTicks, float netHeadYaw, float headPitch) {"
                      "\n\t\t// Use this method to setup the animation and rotation angles"
                      "\n\t}\n")
    file_lines.append("\n\t@Override"
                      "\n\tpublic void renderToBuffer(PoseStack matrixStackIn, VertexConsumer bufferIn, "
                      "int packedLightIn, int packedOverlayIn, float red, float green, float blue, float alpha) {")
    for part in parts:
        if "parent" not in part:
            file_lines.append("\n\t\t%s.render(matrixStack, buffer, packedLight, packedOverlay);" % part["name"])
    file_lines.append("\n\t}\n")


def remove_after_line(index: int, file_lines: List[AnyStr]) -> List[AnyStr]:
    return file_lines[:index]


def get_part_by_name(name: str, parts: List[dict]) -> dict:
    for p in parts:
        if name in p["name"]:
            return p


def get_numbers(line: str) -> List:
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
    nums = [float(num) if "." in num else int(num) for num in nums]
    return nums


def get_booleans(line: str) -> List[float]:
    bools = re.findall(r"(true)|(false)", line)
    bools = [True if "true" in b else False for b in bools]
    return bools


# returns the first word or words seperated by _, meaning its a field name
def get_field_name(line: str) -> str:
    string = re.split(r"[.\s]+", line, maxsplit=2)[1]
    return string


if __name__ == "__main__":
    root = tk.Tk()  # Mandatory for Window
    root.geometry('300x100')  # Window Size
    root.title("Model Converter")  # Window Title

    newline = "%(new_line)%"
    rem_line = "%(r)%"

    btn = tk.Button(root, text='Select File', command=lambda: open_file())  # Button
    btn.grid(row=1, column=1)  # Button Position
    btn.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    tk.mainloop()  # Mandatory for window
