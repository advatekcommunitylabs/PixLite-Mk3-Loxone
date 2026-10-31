


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#define PXL_HOST_TEST
#include "../native/telemetry_core.c"
unsigned int host_ms=0;
int host_case=0, host_requests=0, host_online_seen=0, host_after_disable=0;
int host_offline_after_fault=0, host_bad_command=0, host_old_id_accepted=0;
float host_values[13];
char host_reply[PX_BYTES]="", host_text[3][4096];
jmp_buf host_done;
FILE *host_fopen(char *path, char *mode) {
    FILE *f;
    if (strcmp(path,"/user/pixlite-telemetry.json")!=0 || strcmp(mode,"r")!=0) return NULL;
    if (!host_reply[0]) return NULL;
    f=tmpfile(); if (!f) return NULL;
    fputs(host_reply,f);
    if (host_case==13 && strstr(host_reply,"statisticRead")) { fputc(0,f); fputs("trailing junk",f); }
    rewind(f); return f;
}
float getinput(int index) {
    if (index==0) return host_case==1 ? 0 : (host_case==2 && host_ms>=20000 ? 0 : 1);
    if (index==1) return host_case==9 && host_ms>=15000 ? 300 : 10;
    return 0;
}
char *getinputtext(int index) { return _strdup(host_case==3 ? "bad" : "000000000001"); }
unsigned int getcurrenttime() { return 1000+host_ms/1000-(host_case==8 && host_ms>=35000 ? 100 : 0); }
void setoutput(int index,float value) {
    if (index<0 || index>=13) { host_bad_command=1; return; }
    host_values[index]=value;
    if (index==0 && value==1) host_online_seen=1;
    if (index==0 && value==0 && host_ms>=(host_case==8 ? 35000 : (host_case==9 ? 15000 : 30000))) host_offline_after_fault=1;
}
void setoutputtext(int index,char *text) {
    int id, cap;
    if (index<0 || index>=3 || strlen(text)>=4096) { host_bad_command=1; return; }
    strcpy(host_text[index],text);
    if (index!=0) return;
    host_requests++;
    if (host_case==2 && host_ms>=20000) host_after_disable++;
    if (!px_parse(text)) { host_bad_command=1; return; }
    cap=px_equal(px_key(0,"req"),"constantRead");
    if (!cap && !px_equal(px_key(0,"req"),"statisticRead")) host_bad_command=1;
    id=px_integer(px_key(0,"id"),16000000);
    if (host_case==4 || (host_case==7 && host_ms>=30000) || (host_case==9 && host_ms>=15000)) return;
    if (host_case==5) id--;
    if (cap) sprintf(host_reply,"{\"resp\":\"constantRead\",\"id\":%d,\"result\":{\"constant\":{\"dev\":{\"macAddr\":\"%s\",\"pixPorts\":4,\"pwrBanksIn\":1,\"pwrOut\":true}}}}",id,host_case==10 ? "000000000002" : "000000000001");
    else if (host_case==6) sprintf(host_reply,"{\"resp\":\"statisticRead\",\"id\":%d,\"error\":{\"code\":4}}",id);
    else if (host_case==11) sprintf(host_reply,"{\"resp\":\"statisticRead\",\"id\":%d,\"result\":",id);
    else if (host_case==12 && host_ms>=30000) sprintf(host_reply,"{\"resp\":\"statisticRead\",\"id\":%d,\"result\":{\"statistic\":{}}}",id);
    else sprintf(host_reply,"{\"resp\":\"statisticRead\",\"id\":%d,\"result\":{\"statistic\":{\"dev\":{\"temp\":{\"current\":27},\"bankVolt\":[24200]},\"pixPwrOuts\":{\"fuseGood\":[true,false],\"stat\":[\"Good\",\"OvrCur\"]}}}}",id);
}
void sleep(int ms) {
    host_ms+=ms;
    if (host_ms>=80000) longjmp(host_done,1);
}
#define fopen host_fopen
#include "../native/telemetry_driver.c"
int main(int argc,char **argv) {
    int ok;
    if (argc!=2) return 2;
    host_case=atoi(argv[1]);

    strcpy(host_reply,"{\"resp\":\"statisticRead\",\"id\":2,\"result\":{\"statistic\":{\"dev\":{\"temp\":{\"current\":99}}}}}");
    if (!setjmp(host_done)) px_run();
    ok=!host_bad_command && !host_after_disable;
    if (host_case==0) ok=ok && host_online_seen && host_values[1]==27;
    if (host_case==1 || host_case==3) ok=ok && host_requests==0 && !host_online_seen;
    if (host_case==2) ok=ok && host_online_seen && host_values[0]==0 && host_values[1]==-9999;
    if (host_case>=4 && host_case<=6) ok=ok && !host_online_seen && host_values[0]==0;
    if (host_case==7 || host_case==9) ok=ok && host_online_seen && host_offline_after_fault && host_values[0]==0 && host_values[1]==-9999;
    if (host_case==8) ok=ok && host_online_seen && host_offline_after_fault;
    if (host_case==10 || host_case==11 || host_case==13) ok=ok && !host_online_seen && host_values[0]==0;
    if (host_case==12) ok=ok && host_online_seen && host_values[0]==1 && host_values[1]==-9999 && host_values[2]==0 && host_values[11]==0;
    printf("{\"case\":%d,\"passed\":%d,\"requests\":%d,\"online_seen\":%d,\"final_valid\":%.0f}\n",host_case,ok,host_requests,host_online_seen,host_values[0]);
    return ok ? 0 : 1;
}
