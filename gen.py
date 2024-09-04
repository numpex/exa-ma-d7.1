from jinja2 import Environment, FileSystemLoader
import os

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
        "name": "Samourai",
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
    software_index.write('This chapter presents the software developed within Exa-MA. Each software is described in a dedicated section, with a focus on the features and the general mathematics, the main functionalities, the relevant publications and acknowledgments, and the contact persons.\n')
    # sort software_list with respect to name in lexical order
    software_list = sorted(software_list, key=lambda x: x['name'])
    for software in software_list:
        desc = template_desc.render(software=software)
        name = software['name']
        software['desc'] = desc
        prefix = name.replace('+', 'p').replace(' ','-').lower()
        os.makedirs(f'software/{prefix}', exist_ok=True)
        software['prefix'] = prefix
        software_index.write('\input{software/'+f'{prefix}/{prefix}.tex'+'}\n')
        with open(f'software/{prefix}/{prefix}.tex', 'w') as f:
            f.write(desc)
        # Loop through all categories for the current software
        for category in software['categories']:
            wp = template_wp.render(software=software,wp=category)

            # Ensure the category has an entry in the dictionary
            if category not in latex_content_per_category:
                latex_content_per_category[category] = []
            # Append the rendered content to the category
            software['wp'] = wp
            #print(software['rendered'])
            latex_content_per_category[category].append(software)
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
            for software in software_list:
                name = software['name']
                prefix = software['prefix']
                content_list = software['wp']
                # include the software in the category file
                index.write('\input{software/'+f'{prefix}/{category}/{category}.tex'+'}\n')

