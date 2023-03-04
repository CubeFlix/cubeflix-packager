# packager.py
# Cubeflix packager.

import tempfile, shutil, os, datetime, json
import tarfile, zipfile
import xml.etree.cElementTree as ET
from contextlib import contextmanager

import logging

FORMAT_TARBALL = 'tar'
FORMAT_TARBALL_COMPRESSED = 'tar-gz'
FORMAT_ZIP = 'zip'
FORMAT_FOLDER = 'folder'

class CubeflixPackagerException(Exception):

    """A Cubeflix packager exception."""

def copy_path(src, dest):

    """Copy a path from `src` to `dest`."""

    if os.path.isdir(src):
        shutil.copytree(src, dest)
    else:
        shutil.copy(src, dest)

@contextmanager
def working_directory(path):

    """A context manager to set the current working directory. From https://gist.github.com/nottrobin/3d675653244f8814838a."""

    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)

class Project:

    """A Cubeflix project."""

    def __init__(self, name, path, packages, description, author, license):

        """Create the project."""

        self.name = name
        self.path = path
        self.packages = packages
        self.description = description
        self.author = author
        self.license = license

    def release(self, output_path):

        """Produce releases for the project."""

        logging.info(f"Releasing project {self.name} to path {output_path}...")

        if os.path.isdir(output_path):
            # Folder exists, delete the output folder.
            shutil.rmtree(output_path)

        # Create the output path.
        os.mkdir(output_path)

        # Release each package.
        for package in self.packages:
            # Release the package.
            package.release(output_path)

        # Prepare the manifest file.
        logging.info(f"Writing project manifest...")
        with open(os.path.join(output_path, "MANIFEST.xml"), 'wb') as manifest_file:
            manifest_file.write(self.create_manifest())

        logging.info(f"Released project {self.name} to path {output_path}.")

    def create_manifest(self):

        """Create the manifest file, returning its contents."""

        # Create the XML manifest.
        tree = ET.Element("project")
        
        # Add the project information.
        name = ET.Element("name")
        name.text = self.name
        tree.append(name)

        description = ET.Element("description")
        description.text = self.description
        tree.append(description)

        author = ET.Element("author")
        author.text = self.author
        tree.append(author)

        license = ET.Element("license")
        license.text = self.license
        tree.append(license)

        # Add each package.
        packages = ET.Element("packages")
        for package in self.packages:
            package_item = package.create_manifest_tree()
            packages.append(package_item)
        tree.append(packages)

        # Add the timestamp.
        timestamp = ET.Element("timestamp")
        timestamp.text = str(datetime.datetime.now())
        tree.append(timestamp)

        return ET.tostring(tree, encoding='utf8', method='xml')

class Package:

    """A package for a Cubeflix project."""

    def __init__(self, name, path, contents, output_format, description, version, author, pre_package=None):

        """Create the package. `contents` should be a list of paths to include 
           in the package. Function `pre_package` will be called with the path 
           to the temporary package."""

        self.name = name
        self.path = path
        self.contents = contents
        self.output_format = output_format.lower()
        self.pre_package = pre_package
        self.description = description
        self.version = version
        self.author = author

        assert self.output_format in (FORMAT_TARBALL, \
                                      FORMAT_TARBALL_COMPRESSED, \
                                      FORMAT_ZIP, \
                                      FORMAT_FOLDER), \
                                      "Invalid output format"

    def release(self, output_path):

        """Produce a release for the package."""

        logging.info(f"Releasing package {self.name} to path {output_path} ({self.version})...")

        # Create a temporary folder to prepare the package.
        with tempfile.TemporaryDirectory() as temp_folder:
            # Copy the paths into the temporary folder.
            logging.info(f"Copying files...")
            for path in self.contents:
                # Copy the path into the temporary folder.
                basename = os.path.basename(path)
                copy_path(os.path.join(self.path, path), os.path.join(temp_folder, basename))

            # Prepare the package manifest.
            logging.info(f"Writing package manifest...")
            with open(os.path.join(temp_folder, "MANIFEST.xml"), 'wb') as manifest_file:
                manifest_file.write(self.create_manifest())

            # Call the pre-package function.
            if self.pre_package:
                logging.info(f"Running pre-package script...")
                self.pre_package(temp_folder)

            # Produce the release.
            logging.info(f"Outputting package release (output format {self.output_format})...")
            if self.output_format in (FORMAT_TARBALL, FORMAT_TARBALL_COMPRESSED):
                self._release_tar(output_path, temp_folder)
            elif self.output_format == FORMAT_ZIP:
                self._release_zip(output_path, temp_folder)
            elif self.output_format == FORMAT_FOLDER:
                self._release_folder(output_path, temp_folder)
            else:
                raise CubeflixPackagerException("Invalid output format")
            
        logging.info(f"Released package {self.name} to path {output_path} ({self.version}).")

    def create_manifest_tree(self):

        """Create the manifest XML tree."""

        # Create the XML manifest.
        tree = ET.Element("package", {"format": self.output_format})
        
        # Add the package information.
        name = ET.Element("name")
        name.text = self.name
        tree.append(name)

        description = ET.Element("description")
        description.text = self.description
        tree.append(description)

        version = ET.Element("version")
        version.text = self.version
        tree.append(version)

        author = ET.Element("author")
        author.text = self.author
        tree.append(author)

        return tree

    def create_manifest(self):

        """Create the manifest file, returning its contents."""

        # Create the XML manifest.
        tree = self.create_manifest_tree()

        # Add the timestamp.
        timestamp = ET.Element("timestamp")
        timestamp.text = str(datetime.datetime.now())
        tree.append(timestamp)

        return ET.tostring(tree, encoding='utf8', method='xml')

    def _release_tar(self, output_path, temp_folder):

        """Release the package in tarball format."""

        # Tarball the temp folder.
        with tarfile.open(os.path.join(output_path, self.name + ('.tar.gz' if self.output_format == FORMAT_TARBALL_COMPRESSED else '.tar')), \
                          "w:gz" if self.output_format == FORMAT_TARBALL_COMPRESSED else "w") as tar_file:
            for path in os.listdir(temp_folder):
                tar_file.add(os.path.join(temp_folder, path), path)
    
    def _release_zip(self, output_path, temp_folder):

        """Release the package in zip file format."""

        # Zip the temp folder.
        with zipfile.ZipFile(os.path.join(output_path, self.name + '.zip'), "w") as zip_file:
            for path in os.listdir(temp_folder):
                zip_file.write(os.path.join(temp_folder, path), path)
    
    def _release_folder(self, output_path, temp_folder):

        """Release the package as a folder."""

        copy_path(temp_folder, os.path.join(output_path, self.name))

def load_project(path):

    """Load a project object from a project JSON file."""

    try:
        # Load the project JSON file.
        with open(path, 'r') as json_file:
            project_json = json.load(json_file)

        # Load each package.
        packages = []
        for package in project_json['packages']:
            # Create the pre-package function.
            if 'pre_package' in package:
                def pre_package(path):
                    with working_directory(path):
                        for command in package['pre_package']:
                            os.system(command)
            else:
                pre_package = None

            # Create the package.
            package_obj = Package(package['name'], package['path'], package['contents'], \
                                  package['output_format'], package['description'], package['version'], \
                                  package['author'], pre_package=pre_package)
            packages.append(package_obj)

        # Create the project.
        project = Project(project_json['name'], project_json['path'], packages, project_json['description'], \
                          project_json['author'], project_json['license'])
        
        return project
    
    except Exception as e:
        raise CubeflixPackagerException(str(e))
