# app_builder.py

import os
import shutil
import subprocess

class AppBuilder:
    def __init__(self, app_name, output_directory):
        self.app_name = app_name
        self.output_directory = output_directory
        self.react_native_path = os.path.join(os.getcwd(), app_name)

    def create_project(self):
        subprocess.run(['npx', 'react-native', 'init', self.app_name])

    def build_apk(self):
        os.chdir(self.react_native_path)
        # Build for release
deliverables_path = os.path.join(self.react_native_path, 'android', 'app', 'build', 'outputs', 'apk', 'release')
        subprocess.run(['./gradlew', 'assembleRelease'])
        if os.path.exists(deliverables_path):
            print(f'APK built successfully at: {deliverables_path}')
        else:
            print('APK build failed.')

    def package_apk(self):
        # Assuming APK is built and available in deliverables_path
        apk_source = os.path.join(self.react_native_path, 'android', 'app', 'build', 'outputs', 'apk', 'release', f'{self.app_name}-release.apk')
        destination = os.path.join(self.output_directory, f'{self.app_name}-release.apk')
        shutil.copy(apk_source, destination)
        print(f'APK packaged at: {destination}')

# Usage
if __name__ == '__main__':
    builder = AppBuilder('MyReactNativeApp', '/path/to/output/directory')
    builder.create_project()
    builder.build_apk()
    builder.package_apk()