
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../native/telemetry_core.c"
char cap[PX_BYTES], stats[PX_BYTES];
int load(char *path, char *buffer) {
    FILE *f=fopen(path,"rb"); int n, extra;
    if (!f) return 0;
    n=(int)fread(buffer,1,PX_BYTES-1,f); extra=fgetc(f); fclose(f);
    if (extra!=EOF || n>=PX_BYTES-1) return 0;
    buffer[n]=0; return 1;
}
int main(int argc, char **argv) {
    int ok, i;
    if (argc!=6) return 2;
    if (!load(argv[1],cap) || !load(argv[2],stats)) return 3;
    ok=px_capabilities(cap,atoi(argv[4]),argv[3]);
    if (ok) ok=px_statistics(stats,atoi(argv[5]));
    printf("{\"accepted\":%d,\"ports\":%d,\"banks\":%d,\"power\":%d,\"temp_valid\":%d,\"temperature\":%.6f,\"bank_values\":[",ok,px_ports,px_banks,px_power,px_temp_valid,px_temp);
    for (i=0;i<px_banks;i++) { if (i) printf(","); if (px_bank_valid[i]) printf("%.6f",px_volts[i]); else printf("null"); }
    printf("],\"fuse_good\":[");
    if (px_power) for (i=0;i<px_ports;i++) printf("%s%d",i ? "," : "",px_good[i]);
    printf("],\"fuse_state\":[");
    if (px_power) for (i=0;i<px_ports;i++) printf("%s%d",i ? "," : "",px_state[i]);
    printf("]}\n"); return 0;
}
