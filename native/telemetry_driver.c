






char px_file[80]="/user/pixlite-telemetry.json";
char px_buffer[PX_BYTES], px_message[512], px_mac[13], px_info[1024], px_fuses[2048], px_piece[96];
int px_ident=1, px_pending=0, px_phase=0, px_valid=0, px_enabled=0;
unsigned int px_sent=0, px_received=0, px_last=0, px_ttl=35;

int px_read_file() {
    FILE *f; int n, extra;
    f=fopen(px_file,"r"); if (!f) return 0;
    n=fread(px_buffer,1,PX_BYTES-1,f); extra=fgetc(f); fclose(f);
    if (n<1 || n>=PX_BYTES-1 || extra!=-1) return 0;
    px_buffer[n]=0;
    if (strlen(px_buffer)!=n) return 0;
    return px_parse(px_buffer);
}
void px_unavailable(char *why) {
    int i;
    px_valid=0; px_clear(); setoutput(0,0); setoutput(1,-9999); setoutput(2,0);
    for (i=0;i<PX_BANKS;i++) setoutput(i+3,-9999);
    setoutput(11,0); setoutput(12,-1);
    setoutputtext(1,why); setoutputtext(2,"Fuse status unavailable");
}
void px_publish() {
    int i, mask=0;
    setoutput(0,1); setoutput(1,px_temp_valid ? px_temp : -9999); setoutput(2,px_temp_valid);
    sprintf(px_info,"Temperature: %s",px_temp_valid ? "" : "unavailable");
    if (px_temp_valid) { sprintf(px_piece,"%.2f C",px_temp); strcat(px_info,px_piece); }
    for (i=0;i<PX_BANKS;i++) {
        setoutput(i+3,px_bank_valid[i] ? px_volts[i] : -9999);
        if (px_bank_valid[i]) mask=mask+(1<<i);
        if (i<px_banks) {
            sprintf(px_piece,"; Bank %d: ",i+1); strcat(px_info,px_piece);
            if (px_bank_valid[i]) sprintf(px_piece,"%.3f V",px_volts[i]);
            else strcpy(px_piece,"unavailable");
            strcat(px_info,px_piece);
        }
    }
    setoutput(11,mask); setoutput(12,px_power ? px_ports : 0);
    if (!px_banks) strcat(px_info,"; Bank voltage: unsupported");
    strcpy(px_fuses,px_power ? "" : "Powered-output fuse telemetry: unsupported");
    if (px_power) for (i=0;i<px_ports;i++) {
        sprintf(px_piece,"%s%d:%s/",i ? "; " : "Port ",i+1,px_good[i]<0 ? "unknown" : (px_good[i] ? "fuse good" : "fuse not good"));
        strcat(px_fuses,px_piece);
        if (px_state[i]==0) strcat(px_fuses,"Good");
        else if (px_state[i]==1) strcat(px_fuses,"Inactive");
        else if (px_state[i]==2) strcat(px_fuses,"Overcurrent");
        else if (px_state[i]==3) strcat(px_fuses,"Fuse blown");
        else strcat(px_fuses,"unknown");
    }
    setoutputtext(1,px_info); setoutputtext(2,px_fuses);
}
int px_mac_input() {
    char *s; int i, ok=1;
    s=getinputtext(0);
    if (!s) return 0;
    if (strlen(s)!=12) ok=0;
    if (ok) for (i=0;i<12;i++) if (!((s[i]>='0' && s[i]<='9') || (s[i]>='A' && s[i]<='F'))) ok=0;
    if (ok) { memcpy(px_mac,s,12); px_mac[12]=0; }
    free(s); return ok;
}
void px_send(int phase, unsigned int now) {
    int old=-1;
    if (px_read_file()) old=px_integer(px_key(0,"id"),16000000);
    px_ident++; if (px_ident>16000000) px_ident=1;
    if (px_ident==old) { px_ident++; if (px_ident>16000000) px_ident=1; }
    if (phase==1) sprintf(px_message,"{\"req\":\"constantRead\",\"id\":%d,\"params\":{\"path\":[\"dev\"]}}",px_ident);
    else sprintf(px_message,"{\"req\":\"statisticRead\",\"id\":%d,\"params\":{\"path\":[\"dev.temp.current\",\"dev.bankVolt\",\"pixPwrOuts\"]}}",px_ident);
    px_pending=1; px_phase=phase; px_sent=now;
    setoutputtext(0,px_message);
}

#ifdef PXL_HOST_TEST
void px_run() {
#endif
px_unavailable("Disabled. Commission MAC, reply path and HTTP output before enabling.");
while (1) {
    unsigned int now=getcurrenttime();
    float interval=getinput(1);
    int enabled=getinput(0)>0;
    int result;
    if (!(interval>=10 && interval<=300)) interval=30;
    if (!enabled) {
        if (px_enabled) px_unavailable("Disabled");
        px_enabled=0; px_pending=0; px_last=0;
    } else if (!px_enabled) {
        if (!px_mac_input()) px_unavailable("Commission a 12-digit uppercase MAC before enabling");
        else {
            px_ident=(now%4000000)*4;
            if (px_read_file()) {
                result=px_integer(px_key(0,"id"),16000000);
                if (result>=0) px_ident=(result+32)%16000000;
            }
            px_enabled=1; px_unavailable("Waiting for fresh capabilities"); px_send(1,now);
        }
    } else {
        if ((px_valid && (now<px_received || now-px_received>px_ttl)) || (px_pending && now<px_sent)) {
            px_unavailable("Expired or clock changed"); px_pending=0; px_last=now;
        }
        if (px_pending && now>=px_sent && now-px_sent>5) {
            px_unavailable("No fresh matching HTTP reply"); px_pending=0; px_last=now;
        }
        if (px_pending && px_read_file()) {
            result=px_integer(px_key(0,"id"),16000000);
            if (result==px_ident) {
                px_pending=0;
                if (px_phase==1) {
                    if (px_capabilities(px_buffer,px_ident,px_mac)) px_send(2,now);
                    else { px_unavailable("Capability reply rejected or identity changed"); px_last=now; }
                } else if (px_statistics(px_buffer,px_ident)) {
                    px_valid=1; px_received=now; px_last=now; px_ttl=(unsigned int)interval+5; px_publish();
                } else { px_unavailable("Telemetry reply rejected"); px_last=now; }
            }
        }
        if (!px_pending && (px_last==0 || now<px_last || now-px_last>=interval)) {
            px_unavailable("Waiting for fresh telemetry"); px_send(1,now);
        }
    }
    sleep(250);
}
#ifdef PXL_HOST_TEST
}
#endif
