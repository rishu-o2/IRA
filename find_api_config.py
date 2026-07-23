
import os

for root, dirs, files in os.walk('frontend'):
    for file in files:
        if 'api' in file or 'config' in file or 'constants' in file:
            print(os.path.join(root, file))
