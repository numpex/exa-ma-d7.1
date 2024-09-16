from collections import Counter
from jinja2 import Environment, FileSystemLoader
import os
import pandas as pd
from tabulate import tabulate
import numpy as np
# Specify the path to your Excel file
file_path = 'exama-software.xlsx'
# Define the sheet name or index
sheet_name = 'Software'

# Load the specified range of the Excel sheet into a DataFrame
# Assuming the data starts from the first row and first column, and ends at column 'X' (24th) and row 46
df = pd.read_excel(file_path, sheet_name=sheet_name,engine='openpyxl')

benchmarked_software = df[df['Benchmarked'].isin(
    ['Yes', 'CPU', 'GPU', 'CPU, GPU', 'GPU, CPU'])]

# replace # in Languages with Sharp
benchmarked_software['Languages'] = benchmarked_software['Languages'].str.replace(
    '#', '\#')
benchmarked_software['Interfaces'] = benchmarked_software['Interfaces'].str.replace(
    '_', '\_')
def software_prefix(sofware):
    name = software['Software']
    return name.replace('+', 'p').replace(' ', '-').replace('/', '-').lower()



# get boolean value of 'Yes' or 'No' for columns 
def is_benchmarked_in(wp,row):
    # check that the string WP is in the column name
    return row[f"{wp} Benchmarked"]


def check_ci(entry):
#    print(entry)
    if (entry['DevOps'] == 'None') or pd.isnull(entry['DevOps']):
        return 'None'
    do = entry['DevOps'].replace('\n', ' ')  # Clean up the string

    ci_keywords = ['Continuous Integration', 'Continuous Delivery',
                   'Continuous Deployment', 'Continuous Benchmarking']
    # Find all CI-related keywords that are present
    found_keywords = [keyword for keyword in ci_keywords if keyword in do]

    # Convert list of found keywords to a string separated by commas
    res = ', '.join(found_keywords)

    # Print the software and what was found (for debugging)
    #print(f"{entry['Software']} :  {do} --> {res}")

    return res if res else 'None'  # Return 'None' if no keywords found

def check_packaging(entry):
    package_keywords = ['Packages - Debian', 'Packages - Ubuntu', 'Packages - Fedora',
                        'Packages - GUIX-HPC', 'Packages - Spack', 'Packages - Other']
    if (entry['DevOps'] == 'None') or pd.isnull(entry['DevOps']):
        return 'None'
    do = entry['DevOps'].replace('\n', ' ')  # Clean up the string
    found_keywords = [keyword for keyword in package_keywords if keyword in do]
    res = ', '.join(found_keywords.replace('Packages - ', '') for found_keywords in found_keywords)
    #print(f"{entry['Software']} :  {do} --> {res}")
    return res if res else 'None'


def check_containers(entry):
    container_keywords = ['Container - Docker', 'Container - Singularity',
                          'Container - Apptainer', 'Container - Other']
    if (entry['DevOps'] == 'None') or pd.isnull(entry['DevOps']):
        return 'None'
    do = entry['DevOps'].replace('\n', ' ')  # Clean up
    found_keywords = [keyword for keyword in container_keywords if keyword in do]
    res = ', '.join(found_keywords.replace('Container - ', '') for found_keywords in found_keywords)
    #print(f"{entry['Software']} :  {do} --> {res}")
    return res if res else 'None'


def check_tests(entry):
    test_keywords = ['Test - Unit', 'Test - Verification',
                     'Test - Validation', 'Test - Fuzzy', 'Test - Functional']
    if (entry['DevOps'] == 'None') or pd.isnull(entry['DevOps']):
        return 'None'
    do = entry['DevOps'].replace('\n', ' ')  # Clean up
    found_keywords = [keyword for keyword in test_keywords if keyword in do]
    res = ', '.join(found_keywords.replace('Test - ', '') for found_keywords in found_keywords)
    #print(f"{entry['Software']} :  {do} --> {res}")
    return res if res else 'None'


def generate_latex_table(desc, input_string):
    # Split the input string by comma
    items = [item.strip() for item in input_string.split(',')]

    # Start the LaTeX table
    latex_code = '\\begin{tabular}{!{\\color{numpexgray}\\vrule}p{.25\\linewidth}!{\\color{numpexgray}\\vrule}p{.6885\\linewidth}!{\\color{numpexgray}\\vrule}}\n'
    latex_code += '    \n'
    latex_code += '    \\rowcolor{numpexgray}{\\rule{0pt}{2.5ex}\\color{white}\\bf' + f' {desc}' + '} &  {\\rule{0pt}{2.5ex}\\color{white}\\bf Short Description }\\\\ \n'
    latex_code += '    \n'

    # Add each item as a new row
    for index,item in enumerate(items):
        if index % 2 == 0:
            latex_code += '\\rowcolor{white}'+f'    {item} & provide short description here \\\\\n'
        else:
            latex_code += '\\rowcolor{numpexlightergray}' + \
                f'    {item} & provide short description here \\\\\n'
#        latex_code += '    \\bottomrule\n'

    # End the LaTeX table
    latex_code += '\\end{tabular}'

    return latex_code


def generate_latex_table_simple(input_string):
    if pd.isnull(input_string):
        items = ['None']
    else:
        items = [item.strip() for item in input_string.split(',')]
    items.sort()
    latex_code = '\\begin{tabular}{l}\n'
    for index, item in enumerate(items):
        latex_code += f'{item}\\\\\n'
    latex_code += '\\end{tabular}'

    return latex_code

# Apply functions to create new columns based on 'DevOps'
benchmarked_software['CI'] = benchmarked_software.apply(lambda row: check_ci(row), axis=1)
benchmarked_software['Packaging'] = benchmarked_software.apply(lambda row: check_packaging(row), axis=1)
benchmarked_software['Containers'] = benchmarked_software.apply(lambda row: check_containers(row), axis=1)
benchmarked_software['Tests'] = benchmarked_software.apply(lambda row: check_tests(row), axis=1)


def normalize_archs(arch_string):
    # Define a dictionary to map various input forms to standardized forms
    arch_map = {
        'CPU': ['CPU'],
        'GPU': ['GPU'],
        'Hybrid': ['HYBRID'],
        'Indirect': ['INDIRECT'],
        'Not Yet Benchmarked': ['NOT YET']
    }

    # Split the string by commas and strip spaces
    archs = [arch.strip().upper() for arch in arch_string.split(',')]
    normalized_archs = []

    # Normalize each architecture entry
    for arch in archs:
        found = False
        # Check each category for a match
        for standard, variations in arch_map.items():
            if arch in variations:
                normalized_archs.append(standard)
                found = True
                break
        # If no predefined category matches, classify as 'Unknown'
        if not found:
            normalized_archs.append('Unknown')

    return normalized_archs
    
def normalize_languages(lang_string):
    # Split the string by commas and strip spaces
    languages = [lang.strip() for lang in lang_string.split(',')]
    # Normalize C++ entries
    normalized_languages = []
    for lang in languages:
        if 'C++' in lang:
            # Consolidate all C++ variations
            normalized_languages.append(lang)
        else:
            normalized_languages.append(lang)
    return normalized_languages


def normalize_data_formats(data_string):
    # Split the string by commas and strip spaces
    if pd.isnull(data_string):
        return ['None']
    formats = [format.strip() for format in data_string.split(',')]
    normalized_formats = []
    for format in formats:
        # Normalize specific formats
        if 'JSON' in format.upper():
            normalized_formats.append('JSON')
        elif 'XML' in format.upper():
            normalized_formats.append('XML')
        elif 'YAML' in format.upper():
            normalized_formats.append('YAML')
        elif 'HDF5' in format.upper():
            normalized_formats.append('HDF5')
        elif 'DATABASE' in format.upper():
            normalized_formats.append('Database')
        elif 'DATA-MANAGEMENT' in format.upper():
            normalized_formats.append('Data-management system')
        elif 'IN-HOUSE' in format.upper():
            normalized_formats.append('in-house format')
        elif 'VTK' in format.upper():
            normalized_formats.append('VTK')
        elif 'ENSIGHT' in format.upper():
            normalized_formats.append('Ensight')
        elif 'GMSH' in format.upper():
            normalized_formats.append('Gmsh and associated formats')
        elif 'MED' in format.upper():
            normalized_formats.append('MED')
        elif 'ADIOS' in format.upper():
            normalized_formats.append('Adios')
        elif 'ASCII' in format.upper():
            normalized_formats.append('ASCII')
        elif 'ROOT' in format.upper():
            normalized_formats.append('ROOT')
        elif 'SQL' in format.upper():
            normalized_formats.append('SQL')
        elif 'NETCDF' in format.upper():
            normalized_formats.append('netcdf')
        elif 'MFRONT' in format.upper():
            normalized_formats.append('MFront')
        else:
            normalized_formats.append(format)  # Default case if no matches
    return normalized_formats


def normalize_parallelism(parallelism_string):
    # Split the string by commas and strip spaces
    technologies = [tech.strip() for tech in parallelism_string.split(',')]
    normalized_technologies = []
    for tech in technologies:
        # Normalize specific parallelism technologies
        if 'MPI' in tech.upper():
            normalized_technologies.append('MPI')
        elif 'MULTITHREAD' in tech.upper():
            normalized_technologies.append('Multithread')
        elif 'CHAPEL' in tech.upper():
            normalized_technologies.append('Chapel')
        elif 'GPU' in tech.upper():  # Capture all GPU-related entries
            normalized_technologies.append('GPU')
        elif 'TASK BASED' in tech.upper():  # Generalize all task-based parallelism
            normalized_technologies.append('Task based')
        elif 'C++' in tech.upper() and 'PARALLELISM' in tech.upper():
            normalized_technologies.append('Parallelism - C++')
        else:
            normalized_technologies.append(tech)  # Default case if no matches
    return normalized_technologies


def normalize_devops(devops_string):
    categories = {
        'CI/CD': [],
        'Packaging': [],
        'Testing': [],
        'Containers': []
    }
    if pd.isnull(devops_string):
        return {
            'CI/CD': ['None'],
            'Packaging': ['None'],
            'Testing': ['None'],
            'Containers': ['None']
        }
    entries = [entry.strip() for entry in devops_string.split(',')]

    for entry in entries:
        if 'Continuous' in entry:
            categories['CI/CD'].append(entry)
        elif 'Container' in entry:
            if 'Apptainer' in entry or 'Singularity' in entry:
                categories['Containers'].append('Apptainer/Singularity')
            else:
                categories['Containers'].append(entry.split('-')[1].strip())
        elif 'Packages' in entry:
            # Group Debian and Ubuntu into Debian-based packaging
            if 'Debian' in entry or 'Ubuntu' in entry:
                categories['Packaging'].append('Debian-based')
            else:
                categories['Packaging'].append(entry.split('-')[1].strip())
        elif 'Test' in entry:
            print(entry)
            categories['Testing'].append(entry.split('-')[1].strip())
    if not categories['CI/CD']:
        categories['CI/CD'].append('None')
    if not categories['Packaging']:
        categories['Packaging'].append('None')
    if not categories['Containers']:
        categories['Containers'].append('None')
    if not categories['Testing']:
        categories['Testing'].append('None')
    
    return categories

stats_software=benchmarked_software

stats_software['Benchmarked'] = stats_software['Benchmarked'].apply(
    lambda x: ', '.join(normalize_archs(x)))
# Apply normalization to the Languages column
stats_software['Languages'] = stats_software['Languages'].apply(
    lambda x: ', '.join(normalize_languages(x)))
stats_software['Parallelism'] = stats_software['Parallelism'].apply(
    lambda x: ', '.join(normalize_parallelism(x)))
stats_software['Data'] = stats_software['Data'].apply(
    lambda x: ', '.join(normalize_data_formats(x)))
stats_software['DevOps CI/CD'] = stats_software['DevOps'].apply(
    lambda x: ', '.join(normalize_devops(x)['CI/CD']))
stats_software['DevOps Packaging'] = stats_software['DevOps'].apply(
    lambda x: ', '.join(normalize_devops(x)['Packaging']))
stats_software['DevOps Containers'] = stats_software['DevOps'].apply(
    lambda x: ', '.join(normalize_devops(x)['Containers']))
stats_software['DevOps Testing'] = stats_software['DevOps'].apply(
    lambda x: ', '.join(normalize_devops(x)['Testing']))

def count_frequencies(df,column,debug=False):
    items = []
    df[column].dropna().apply(lambda x: items.extend(x.split(', ')))
    if debug:
        print(items)
    return Counter(items)

archs_freq = count_frequencies(stats_software,'Benchmarked')
languages_freq = count_frequencies(stats_software,'Languages')
parallelism_freq = count_frequencies(stats_software,'Parallelism')
data_freq = count_frequencies(stats_software,'Data')
devops_cicd_freq = count_frequencies(stats_software, 'DevOps CI/CD')
devops_packaging_freq = count_frequencies(stats_software, 'DevOps Packaging')
devops_containers_freq = count_frequencies(stats_software, 'DevOps Containers')
devops_testing_freq = count_frequencies(stats_software, 'DevOps Testing',debug=True)


def tikz_pie_chart(data, title, caption, label):
    colors = [
        "red",       # Bright enough to contrast well with black
        "orange",    # Good contrast with black
        "yellow",    # Excellent for black text
        "lime",      # Lighter shade of green
        "skyblue",   # A lighter blue that contrasts well with black
        "pink",      # Naturally light and offers good readability
        "cyan",      # Light and vibrant, contrasting with black
        "magenta",   # Bright and pops against black
        "peach",     # Soft and visible against black
        "lavender"   # Light and easy on the eyes with black text
    ]
    chart = "\\begin{figure}[H]\n\\centering\n\\begin{tikzpicture}\n"
    chart += "\\pie[text=legend, color={"
    chart += ", ".join(colors[:len(data)]) + "}, sum=auto]"
    chart += "{"
    chart += ", ".join([f"{value}/{key}" for key, value in data.items()])
    chart += "}\n\\end{tikzpicture}\n"
    chart += f"\\caption{{{caption}}}\n"
    chart += f"\\label{{fig:{label}}}\n"
    chart += "\\end{figure}\n"
    return chart

arch_chart = tikz_pie_chart(archs_freq, "Architectures", caption="Distribution of hardware architectures", label="arch")
languages_chart = tikz_pie_chart(languages_freq, "Languages", caption="Distribution of programming languages", label="languages")
parallelism_chart = tikz_pie_chart(parallelism_freq, "Parallelism", caption="Distribution of parallelism technologies", label="parallelism")  
data_chart = tikz_pie_chart(data_freq, "Data", caption="Distribution of data formats", label="data")
devops_cicd_chart = tikz_pie_chart(
    devops_cicd_freq, "DevOps", caption="Distribution of DevOps CI/CD/CD", label="devops-cicd")
devops_packaging_chart = tikz_pie_chart(
    devops_packaging_freq, "DevOps", caption="Distribution of DevOps Packaging", label="devops-packaging")
devops_containers_chart = tikz_pie_chart(
    devops_containers_freq, "DevOps", caption="Distribution of DevOps Containers", label="devops-containers")
devops_testing_chart = tikz_pie_chart(
    devops_testing_freq, "DevOps", caption="Distribution of DevOps Testing", label="devops-testing")        


#for wp in range(1,8):
#    df[f'Benchmarked in WP{wp}'] = df.apply(
#        lambda row: is_benchmarked_in(f'WP{wp}', row), axis=1)
#    b_df=df[df[f'Benchmarked in WP{wp}'] == True]['Software']
#    print(f"WP{wp} : {b_df.values}")

#print("feel++:", is_benchmarked_in('WP1',df[df['Software']=='Feel++']))
import json
for index,software in benchmarked_software.iterrows():

    software_json = json.loads(software.to_json())

    print(software_json)

# Sample data, replace with your actual data source
software_list = [
    {
        "categories": [ "WP7" ],
        "name": "Arcane Framework",
        "email": "lydie.grospellier@cea.fr",
        "architecture": "HYBRID",
        "repository": "https://github.com/arcaneframework/framework"
    },
    {
        "categories": ["WP1"],
        "name": "CGAL",
        "email": "pierre.alliez@inria.fr",
        "architecture": "CPU",
        "repository": "https://github.com/CGAL"
    },
    {
        "categories": ["WP2"],
        "name": "Scimba",
        "email": "emmanuel.franck@inria.fr, matthieu.boileau@math.unistra.fr, victor.michel-dansac@inria.fr",
        "architecture": "GPU",
        "repository": "https://gitlab.inria.fr/scimba/scimba"
    },
    {
        "categories": ["WP1","WP2","WP3","WP4","WP5","WP7"],
        "name": "Feel++",
        "email": "vincent.chabannes@cemosis.fr, christophe.prudhomme@cemosis.fr",
        "architecture": "CPU",
        "repository": "https://github.com/feelpp/feelpp"
    },
    {
        "categories": ["WP1", "WP2", "WP3", "WP4", "WP7"],
        "name": "FreeFem++",
        "email": "frederic.hecht@sorbonne-universite.fr, pierre.jolivet@sorbonne-universite.fr",
        "architecture": "CPU",
        "repository": "https://github.com/FreeFem/FreeFem-sources"
    },
    {
        "categories": ["WP1","WP3","WP4"],
        "name": "Hawen",
        "email": "florian.faucher@inria.fr",
        "architecture": "CPU",
        "repository": "https://gitlab.com/ffaucher/hawen"
    },
    {
        "categories": ["WP1"],
        "name": "Samurai",
        "email": "loic.gouarin@polytechnique.edu",
        "architecture": "CPU",
        "repository": "https://github.com/hpc-maths/samurai"
    },
    {
        "categories": ["WP3"],
        "name": "HPDDM",
        "email": "pierre.joliv.et",
        "architecture": "CPU",
        "repository": "https://github.com/hpddm/hpddm"
    },
    {
        "categories": ["WP3"],
        "name": "MaHyCo",
        "email": "jean-philippe.perlat@cea.fr",
        "architecture": "HYBRID",
        "repository": "URL not visible"
    },
    {
        "categories": ["WP7"],
        "name": "MANTA",
        "email": "olivier.jamond@cea.fr",
        "architecture": "CPU",
        "repository": "URL not visible"
    },
    {
        "categories": ["WP3"],
        "name": "Maphys++",
        "email": "gilles.marait@inria.fr",
        "architecture": "HYBRID",
        "repository": "https://gitlab.inria.fr/solverstack/maphys/maphyspp"
    },
    {
        "categories": ["WP1"],
        "name": "MMG-ParMMG",
        "email": "No visible email",
        "architecture": "CPU",
        "repository": "URL not visible"
    },
    {
        "categories": ["WP5"],
        "name": "pBB",
        "email": "noureddine.melab@univ-lille.fr",
        "architecture": "HYBRID",
        "repository": "https://gitlab.inria.fr/igmys/permutationbb"
    },
    {
        "categories": ["WP7"],
        "name": "TRUST Platform",
        "email": "pierre.ledac@cea.fr",
        "architecture": "HYBRID",
        "repository": "https://github.com/cea-trust-platform"
    },
    {
        "categories": ["WP6"],
        "name": "Uranie",
        "email": "rudy.chocat@cea.fr, jean-baptiste.blanchard@cea.fr",
        "architecture": "CPU",
        "repository": "https://sourceforge.net/projects/uranie/"
    },
    {

        "categories": ["WP5"],
        "name": "Zellij",
        "email": "el-ghazali.talbi@univ-lille.fr",
        "architecture": "GPU",
        "repository": "https://github.com/ThomasFirmin/zellij"
    }
]
WPs = {
    "WP1": "WP1 - Discretization",
    "WP2": "WP2 - Model order, Surrogate, Scientific Machine Learning methods",
    "WP3": "WP3 - Solvers",
    "WP4": "WP4 - Data assimilation",
    "WP5": "WP5 - Optimization",
    "WP6": "WP6 - Uncertainty quantification",
    "WP7": "Mini-Apps and Proxy-Apps"
}

# Set up Jinja2 environment for LaTeX
env = Environment(
    block_start_string='\BLOCK{',
    block_end_string='}',
    variable_start_string='\VAR{',
    variable_end_string='}',
    comment_start_string='\#{',
    comment_end_string='}',
    # Adjust the path to where your template file is stored
    loader=FileSystemLoader(searchpath="./")
)

# Load template from file
template_desc = env.get_template('templates/desc-software.tex')
template_wp = env.get_template('templates/wp-software.tex')

# for software in software_list:
#     rendered = template.render(software=software)
# 
#     # Define file name
#     file_name = f"sections/sw-{software['name'].replace(' ', '_').lower()}.tex"
#     with open(file_name, 'w') as f:
#         f.write(rendered)
#     print(f"Generated LaTeX file for {software['name']} at {file_name}")
# 

# Directory for sections if not already created
os.makedirs('chapters', exist_ok=True)
os.makedirs('software',exist_ok=True)

# Dictionary to store LaTeX content per category
latex_content_per_category = {}
with open(f'chapters/software.tex', 'w') as software_index:
    software_index.write('\clearpage\n\chapter{Software}\n')
    software_index.write('\label{sec:software}\n')
    software_index.write(
    """
    This chapter presents the software developed within Exa-MA, focusing on features, mathematics, functionalities, publications, acknowledgments, and contact details.

    First, we present some general statistics about the software identified for Exa-MA that will present some benchmarking results. 
    Other software (new or existing) will be included in the future version of this document.
    """)

    software_index.write(
        """
        \paragraph{Architectures}
        The following pie chart~\\ref{fig:arch} shows the distribution of hardware architectures used.
        """)
    software_index.write(arch_chart)
    # Programming Languages Pie Chart
    software_index.write(
        """
        \paragraph{Programming Languages}
        The following pie chart~\\ref{fig:languages} shows the distribution of programming languages used, highlighting the variety of computational solutions employed.
        """)
    software_index.write(languages_chart)

    # Parallelism Techniques Pie Chart
    software_index.write(
        """
        \paragraph{Parallelism Technology}
        The pie chart~\\ref{fig:parallelism} below represents the parallelism techniques used in Exa-MA software selected for this document.
        """)
    software_index.write(parallelism_chart)

    # Data Formats Pie Chart
    software_index.write(
        """
        \paragraph{Data Formats}
        The chart~\\ref{fig:data} shows the supported data formats, for flexibility and compatibility in data handling, supported by Exa-MA software selected for this document.
        """)
    software_index.write(data_chart)

    # DevOps - CI/CD Pie Chart
    software_index.write(
        """
        \paragraph{DevOps - CI/CD}
        The pie chart~\\ref{fig:devops-cicd} below displays the support of continuous integration and deployment practices as well as continuous benchmarking, showcasing systematic software updates, quality maintenance and performance regression.
        """)
    software_index.write(devops_cicd_chart)

    # DevOps - Packaging Pie Chart
    software_index.write(
        """
        \paragraph{DevOps - Packaging}
        The next chart~\\ref{fig:devops-packaging} shows different packaging methods used, which help in the distribution and management of software.
        """)
    software_index.write(devops_packaging_chart)

    # DevOps - Containers Pie Chart
    software_index.write(
        """
        \paragraph{DevOps - Containers}
        The pie chart~\\ref{fig:devops-containers} displays the use of container technologies, which help encapsulate the software to run reliably in various environments.
        """)
    software_index.write(devops_containers_chart)

    # DevOps - Testing Pie Chart
    software_index.write(
        """
        \paragraph{DevOps - Testing}
        The following pie chart~\\ref{fig:devops-testing} details the testing practices adopted, illustrating the commitment to software reliability and functionality.
        """)
    software_index.write(devops_testing_chart)

    # sort software_list with respect to name in lexical order
    software_list = sorted(software_list, key=lambda x: x['name'])
    for index,software in benchmarked_software.iterrows():
        software_json = json.loads(software.to_json())
        software_json['name'] = software['Software']
        for column_name in ['Emails','Consortium', 'Partner', 'License', 'Languages', 'Benchmarked', 'Parallelism', 'Data', 'DevOps', 'CI', 'Packaging', 'Containers', 'Tests', 'Resilience','Interfaces']:
            software_json[column_name] = generate_latex_table_simple(
               input_string=software[column_name])

        desc = template_desc.render(software= software_json)
        name = software['Software']
        prefix = software_prefix(software)
        os.makedirs(f'software/{prefix}', exist_ok=True)
        software_json['prefix'] = prefix
        software_index.write('\input{software/'+f'{prefix}/{prefix}.tex'+'}\n')
        
        with open(f'software/{prefix}/{prefix}.tex', 'w') as f:
            f.write(desc)
        # Loop through all categories for the current software
        for wpindex in range(1,7):
            category = f'WP{wpindex}'
            if is_benchmarked_in(category,software):
                software_json = json.loads(software.to_json())
                software_json['name'] = software['Software']
                software_json['WP'] = generate_latex_table(
                    desc="Features", input_string=software[category])
                for column_name in ['Emails', 'Consortium', 'Partner', 'License', 'Languages', 'Benchmarked', 'Parallelism', 'Data', 'DevOps', 'CI', 'Packaging', 'Containers', 'Tests', 'Resilience', 'Interfaces']:
                    software_json[column_name] = generate_latex_table_simple(
                        input_string=software[column_name])
                software_json['Emails'] = generate_latex_table_simple(
                    input_string=software['Emails'])
                wp = template_wp.render(software=software_json,wp=category)
                # Ensure the category has an entry in the dictionary
                if category not in latex_content_per_category:
                    latex_content_per_category[category] = []
                # Append the rendered content to the category
                software_json['wp'] = wp
                #print(software['rendered'])
                latex_content_per_category[category].append(software_json)
                os.makedirs(f'software/{prefix}/{category}', exist_ok=True)
                with open(f'software/{prefix}/{category}/{category}.tex', 'w') as f:
                    f.write(wp)
                print(f"- Generated LaTeX file for {name} in category {category}: software/{prefix}/{category}/{category}.tex")


# sort latex_content_per_category with respect to category in lexical order
latex_content_per_category = dict(sorted(latex_content_per_category.items()))
# Now, generate a .tex file for each category containing all relevant software entries
with open('chapters/00-index.tex', 'a') as main_index:
    for category, software_list in latex_content_per_category.items():
        # create the directory for the category
        os.makedirs(f'chapters/{category}', exist_ok=True)
        main_index.write('\chapter{'+f'{WPs[category]}'+'}\n')
        main_index.write('\clearpage\n\subimport{'+f'./{category}'+'}{00-index}\n\n')
        with open(f'chapters/{category}/00-index.tex', 'w') as index:
            for i,software in benchmarked_software.iterrows():
                #software_json = software.to_json()
                #name = software['Software']

                prefix = software_prefix(software)
                #content_list = software['wp']
                # include the software in the category file
                if is_benchmarked_in(category,software):
                    index.write('\input{software/'+f'{prefix}/{category}/{category}.tex'+'}\n')
                #index.write('\input{software/'+f'{prefix}/{category}/{category}.tex'+'}\n')

