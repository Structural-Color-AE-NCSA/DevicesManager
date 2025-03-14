
import os
import argparse

def replace_placeholders(input_file, output_file, BedTemp, Pressure, PrintSpeed, Z_delta_height):
    # Open the input file and read the content
    with open(input_file, 'r') as file:
        content = file.read()
    content = replace_placeholders_content(content, BedTemp, Pressure, PrintSpeed, Z_delta_height)
    # Write the modified content to the output file
    with open(output_file, 'w') as file:
        file.write(content)
    print(f"Replacements complete. The output file has been saved as '{output_file}'.")

def replace_placeholders_content(content, BedTemp, Pressure, PrintSpeed, Z_delta_height):
    # Replace placeholders with the actual values
    if BedTemp:
        content = content.replace(f"R(BedTemp)", "R"+str(BedTemp))  # Replace R(BedTemp)
    if PrintSpeed:
        content = content.replace(f"F(PrintSpeed)", "F"+str(PrintSpeed))  # Replace F(PrintSpeed)
    if Pressure:
        content = content.replace(f"P(PRESSURE)", str(Pressure))  # Replace P(Pressure)
    # if Z_delta_height:
    #     content = content.replace(f"Z(Delta_Height)", "Z"+str(Z_delta_height))
    return content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="demo color updates")
    parser.add_argument("-i", "--input_file", required=True, help="input file")
    parser.add_argument("-o", "--output_file", required=True, help="output file")
    parser.add_argument("-p", "--pressure", required=True, help="the value of pressure")
    parser.add_argument("-s", "--speed", required=True, help="print speed")
    parser.add_argument("-b", "--bed_temp", required=True, help="bed temp")
    parser.add_argument("-z", "--delta_z_height", required=True, help="delta z height")
    args = parser.parse_args()
    replace_placeholders(args.input_file, args.output_file, args.bed_temp, args.pressure, args.speed, args.delta_z_height)