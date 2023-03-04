import packager
PATH = "c:/users/kevin chen/projects/cubeflix-packager"

my_package = packager.Package("source", PATH, \
                              ["packager.py", "README.md"], \
                              packager.FORMAT_TARBALL, \
                              "cubeflix-packager source code (Python).", \
                              "1.0.0", \
                              "cubeflix")
proj = packager.Project("cubeflix-packager", PATH, [my_package], "The Cubeflix internal packager utility. Built in Python.", "cubeflix", "none")
proj.release("release")