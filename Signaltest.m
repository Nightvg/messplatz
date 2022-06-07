% record and plot signals for checking quality

[EMG1,EMG2,ECG,EDA,BR] = ReadSplitData('Com16',500000, 300, 0.2);
movefile EMG1.txt EMG1_Test.txt;
movefile EMG2.txt EMG2_Test.txt;
movefile ECG.txt ECG_Test.txt;
movefile EDA.txt BR_Test.txt;
movefile BR.txt BR_Test.txt;

subplot(5,1,1)
plot(str2double(EMG1));

subplot(5,1,2)
plot(str2double(EMG2));

subplot(5,1,3)
plot(str2double(ECG));

subplot(5,1,4)
plot(str2double(EDA));

subplot(5,1,5)
plot(str2double(BR));
