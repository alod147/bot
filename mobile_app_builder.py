import React from 'react';
import { View, Button, Alert } from 'react-native';

const MobileAppBuilder = () => {
  const buildApp = () => {
    // Logic to configure the build settings
    // Simulated build process
    Alert.alert('Building APK...');
    setTimeout(() => {
      Alert.alert('APK generated successfully!');
    }, 2000);
  };

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Button title="Build Android App" onPress={buildApp} />
    </View>
  );
};

export default MobileAppBuilder;
