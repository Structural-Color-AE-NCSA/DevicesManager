
import os
import argparse

def replace_placeholders(input_file, output_file, BedTemp, Pressure, PrintSpeed):
    # Open the input file and read the content
    with open(input_file, 'r') as file:
        content = file.read()

    # Replace placeholders with the actual values
    content = content.replace(f"R(BedTemp)", str(BedTemp))  # Replace R(BedTemp)
    content = content.replace(f"F(PrintSpeed)", str(PrintSpeed))  # Replace F(PrintSpeed)
    content = content.replace(f"P(PRESSURE)", str(Pressure))  # Replace P(Pressure)

    # Write the modified content to the output file
    with open(output_file, 'w') as file:
        file.write(content)
    print(f"Replacements complete. The output file has been saved as '{output_file}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="demo color updates")
    parser.add_argument("-i", "--input_file", required=True, help="input file")
    parser.add_argument("-o", "--output_file", required=True, help="output file")
    parser.add_argument("-p", "--pressure", required=True, help="the value of pressure")
    parser.add_argument("-s", "--speed", required=True, help="print speed")
    parser.add_argument("-b", "--bed_temp", required=True, help="bed temp")
    args = parser.parse_args()
    replace_placeholders(args.input_file, args.output_file, args.pressure, args.speed, args.bed_temp)