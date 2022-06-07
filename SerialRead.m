% this function is for recording the signals 

function [SerData,length] = SerialRead(COMPort, Baudrate, fsample_Hz, time_min)

s = serial(COMPort);
s.BaudRate = Baudrate;
length = time_min*60*fsample_Hz;
SerData = strings([length,2]); 
i = 1;
fopen(s);

tic; %start timer;
flushinput(s);
while toc < (time_min*60) % check elapsed time
    
if ~isempty(s.BytesAvailable)
    
  SerData(i,1) = fgetl(s);
  SerData(i,2) = datetime('now','Format','HH:mm:ss.SSS'); 
  i = i+1;
     
else
 disp('Fehler'); 
end
end
fclose(s);
end 