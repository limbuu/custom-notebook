from __future__ import absolute_import
import os
if __name__ == '__main__':
    print(os.environ)
    from notebook import notebookapp as app
    app.launch_new_instance()
