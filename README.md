# Master Thesis - New Tools for the Analysis of Cytomine user viewing Behavior

This software, connects to a Cytomine website installation (E.G. http://www.cytomine.be/) to download data concerning user behavior when observing images.
This project promoted by Raphael Marée mainly consists in the study of the medicial students of Ulg's use of Cytomine. Images contains information on cells and students' goals are to understand what's on the images.
At the end of the year, students take an exam on what they learned from Cytomine. One of the goals with this project is to try to find correlations between how students observed these images and the grades they obtained.
This project contains multiple modules that rely on each other:
- download_data : Downloads positions, annotations, and other information stored from a student viewing images from the website (Can take a long time depending on the number of images and students).
- data_manager : Organizes all the data, and generates important information, Gazemaps, and scan paths. (slow when generating Gazemaps and Scan Paths due to the quantity).
- data_learning : From all the information extracted, uses machine learning techniques to draw conclusions.


## Cytomine References :

- URL: http://www.cytomine.be/
- Logo: http://www.cytomine.be/logo/logo.png
- Scientific paper: Raphaël Marée, Loïc Rollus, Benjamin Stévens, Renaud Hoyoux, Gilles Louppe, Rémy Vandaele, Jean-Michel Begon, Philipp Kainz, Pierre Geurts and Louis Wehenkel. Collaborative analysis of multi-gigapixel imaging data using Cytomine, Bioinformatics, DOI: 10.1093/bioinformatics/btw013, 2016. http://bioinformatics.oxfordjournals.org/cgi/content/abstract/btw013?ijkey=dQzEgmXVozFRPPf&keytype=ref 


Cytomine (http://www.cytomine.be/) client and utilities in Python.

Cytomine client contains functions to import/export data (projects, ontologies, images, users, annotations, softwares, ...) from/to Cytomine core server based on the RESTful API.

Cytomine utilities contains various functions including ones to access whole slide images (tiles,...) and basic image processing tools.

See examples in https://github.com/cytomine/Cytomine-python-client/tree/master/client/examples and https://github.com/cytomine/Cytomine-python-client/tree/master/utilities/examples

The client is automatically installed with the Docker/Bootstrap procedure, however it is possible to install it independently
on remote computers. See installation instructions here:
http://doc.cytomine.be/pages/viewpage.action?pageId=12321357