from messplatz import PacketManager

if __name__ == '__main__':
    pM = PacketManager()
    pM.attachReader()
    pM.start()