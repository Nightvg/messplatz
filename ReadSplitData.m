% this function calls "SerialRead", splits the strings coming out 
% of the buffer and allocates the single values to corresponding arrays.


function [EMG1,EMG2,ECG,EDA,BR] = ReadSplitData(COMPort,Baudrate, fsample_Hz, time_min)

[SerData, length] = SerialRead(COMPort,Baudrate, fsample_Hz, time_min);

x = length/30;
length2 = round(x);
EMG1 = strings([length,2]);
EMG2 = strings([length,2]);
ECG = strings([length,2]);
EDA = strings([length2,2]);
BR = strings([length2,2]);

k = 1;

for i = 1:length
    
    a = SerData(i,1);
    b = split(a,",");
    n = numel(b);
    
    switch n
        case 3
            EMG1(i,1) = b(1,1);
            EMG1(i,2) = SerData(i,2);
            EMG2(i,1) = b(2,1);
            EMG2(i,2) = SerData(i,2);
            ECG(i,1) = b(3,1);
            ECG(i,2) = SerData(i,2);
            
        case 5
            EMG1(i,1) = b(1,1);
            EMG1(i,2) = SerData(i,2);
            EMG2(i,1) = b(2,1);
            EMG2(i,2) = SerData(i,2);
            ECG(i,1) = b(3,1);
            ECG(i,2) = SerData(i,2);
            BR(k,1) = b(4,1);
            BR(k,2) = SerData(i,2);
            EDA(k,1)= b(5,1);
            EDA(k,2) = SerData(i,2);
            
            k = k+1;
            
        otherwise
            A = 'Blödsinn';
            fprintf('%s',A);
    end
end

% writing data to txt file

writematrix(EMG1, 'EMG1.txt');
writematrix(EMG2, 'EMG2.txt');
writematrix(ECG, 'ECG.txt');
writematrix(EDA, 'EDA.txt');
writematrix(BR, 'BR.txt');

end