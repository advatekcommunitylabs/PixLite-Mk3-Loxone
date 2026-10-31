



#define PX_BYTES 4096
#define PX_TOKENS 256
#define PX_PORTS 32
#define PX_BANKS 8
char *px_json;
int px_pos, px_len, px_count;
int px_start[PX_TOKENS], px_end[PX_TOKENS], px_next[PX_TOKENS], px_type[PX_TOKENS];
int px_ports, px_banks, px_power, px_temp_valid;
float px_temp, px_volts[PX_BANKS];
int px_bank_valid[PX_BANKS], px_good[PX_PORTS], px_state[PX_PORTS];

void px_space() {
    while (px_pos < px_len && (px_json[px_pos]==' ' || px_json[px_pos]=='\r' || px_json[px_pos]=='\n' || px_json[px_pos]=='\t')) px_pos++;
}
int px_equal(int token, char *value) {
    int n;
    if (token < 0 || token >= px_count) return 0;
    n=px_end[token]-px_start[token];
    return n==strlen(value) && strncmp(px_json+px_start[token],value,n)==0;
}
int px_same(int a, int b) {
    int n=px_end[a]-px_start[a];
    return n==px_end[b]-px_start[b] && strncmp(px_json+px_start[a],px_json+px_start[b],n)==0;
}
int px_value(int depth) {
    int t, c, k, prior, v, digit;
    if (depth>12 || px_count>=PX_TOKENS) return -1;
    px_space();
    if (px_pos>=px_len) return -1;
    t=px_count++;
    px_start[t]=px_pos;
    c=px_json[px_pos];
    if (c=='{' || c=='[') {
        px_type[t]=c; px_pos++; px_space();
        if (px_pos<px_len && px_json[px_pos]==(c=='{' ? '}' : ']')) px_pos++;
        else {
            while (1) {
                if (c=='{') {
                    k=px_value(depth+1);
                    if (k<0 || px_type[k]!='"') return -1;
                    prior=t+1;
                    while (prior<k) {
                        if (px_same(prior,k)) return -1;
                        prior=px_next[prior+1];
                    }
                    px_space();
                    if (px_pos>=px_len || px_json[px_pos++]!=':') return -1;
                }
                v=px_value(depth+1); if (v<0) return -1;
                px_space(); if (px_pos>=px_len) return -1;
                digit=px_json[px_pos++];
                if (digit==(c=='{' ? '}' : ']')) break;
                if (digit!=',') return -1;
            }
        }
    } else if (c=='"') {
        px_type[t]='"'; px_pos++; px_start[t]=px_pos;
        while (px_pos<px_len && px_json[px_pos]!='"') {
            if ((unsigned char)px_json[px_pos]<32 || px_json[px_pos]=='\\') return -1;
            px_pos++;
        }
        if (px_pos>=px_len) return -1;
        px_end[t]=px_pos; px_pos++; px_next[t]=px_count; return t;
    } else if (c=='t' || c=='f' || c=='n') {
        px_type[t]=c;
        k=c=='t' ? 4 : (c=='f' ? 5 : 4);
        if (px_pos+k>px_len || strncmp(px_json+px_pos,c=='t' ? "true" : (c=='f' ? "false" : "null"),k)!=0) return -1;
        px_pos+=k;
    } else {
        px_type[t]='N';
        if (px_json[px_pos]=='-') px_pos++;
        if (px_pos>=px_len) return -1;
        if (px_json[px_pos]=='0') px_pos++;
        else {
            k=px_pos;
            while (px_pos<px_len && px_json[px_pos]>='0' && px_json[px_pos]<='9') px_pos++;
            if (px_pos==k) return -1;
        }
        if (px_pos<px_len && px_json[px_pos]=='.') {
            px_pos++; k=px_pos;
            while (px_pos<px_len && px_json[px_pos]>='0' && px_json[px_pos]<='9') px_pos++;
            if (px_pos==k) return -1;
        }
        if (px_pos<px_len && (px_json[px_pos]=='e' || px_json[px_pos]=='E')) {
            px_pos++;
            if (px_pos<px_len && (px_json[px_pos]=='+' || px_json[px_pos]=='-')) px_pos++;
            k=px_pos;
            while (px_pos<px_len && px_json[px_pos]>='0' && px_json[px_pos]<='9') px_pos++;
            if (px_pos==k) return -1;
        }
    }
    px_end[t]=px_pos; px_next[t]=px_count; return t;
}
int px_parse(char *text) {
    px_json=text; px_pos=0; px_count=0; px_len=(int)strlen(text);
    if (px_len<=0 || px_len>=PX_BYTES || px_value(0)!=0) return 0;
    px_space(); return px_pos==px_len && px_type[0]=='{';
}
int px_key(int object, char *key) {
    int i;
    if (object<0 || object>=px_count || px_type[object]!='{') return -1;
    i=object+1;
    while (i<px_next[object]) {
        if (px_equal(i,key)) return i+1;
        i=px_next[i+1];
    }
    return -1;
}
int px_at(int array, int index) {
    int i;
    if (array<0 || px_type[array]!='[') return -1;
    i=array+1;
    while (index>0 && i<px_next[array]) { i=px_next[i]; index--; }
    return i<px_next[array] ? i : -1;
}
int px_integer(int t, int maximum) {
    int p, v=0, digit;
    if (t<0 || px_type[t]!='N') return -1;
    for (p=px_start[t];p<px_end[t];p++) {
        digit=px_json[p]-'0';
        if (digit<0 || digit>9 || v>(maximum-digit)/10 || digit>maximum) return -1;
        v=v*10+digit;
    }
    return v;
}
int px_number(int t, float *value) {
    char number[40]; int n;
    if (t<0 || px_type[t]!='N') return 0;
    n=px_end[t]-px_start[t]; if (n<1 || n>=40) return 0;
    memcpy(number,px_json+px_start[t],n); number[n]=0; *value=(float)atof(number);
    return *value==*value && *value>=-1.0e30 && *value<=1.0e30;
}
int px_reply(char *text, char *method, int ident) {
    int t;
    if (!px_parse(text)) return -1;
    if (!px_equal(px_key(0,"resp"),method) || px_integer(px_key(0,"id"),16000000)!=ident) return -1;
    t=px_key(0,"error"); if (t>=0) return -1;
    t=px_key(0,"result"); return t>=0 && px_type[t]=='{' ? t : -1;
}
void px_clear() {
    int i;
    px_temp=0; px_temp_valid=0;
    for (i=0;i<PX_BANKS;i++) { px_volts[i]=0; px_bank_valid[i]=0; }
    for (i=0;i<PX_PORTS;i++) { px_good[i]=-1; px_state[i]=-1; }
}
int px_capabilities(char *text, int ident, char *mac) {
    int r, d, p, m, ports, banks;
    px_ports=0; px_banks=0; px_power=0; px_clear();
    r=px_reply(text,"constantRead",ident);
    d=px_key(px_key(r,"constant"),"dev");
    m=px_key(d,"macAddr");
    if (d<0 || m<0 || px_type[m]!='"' || strlen(mac)!=12 || !px_equal(m,mac)) return 0;
    ports=px_integer(px_key(d,"pixPorts"),PX_PORTS);
    banks=px_integer(px_key(d,"pwrBanksIn"),PX_BANKS);
    p=px_key(d,"pwrOut");
    if (ports<1 || banks<0 || p<0 || (px_type[p]!='t' && px_type[p]!='f')) return 0;
    px_ports=ports; px_banks=banks; px_power=px_type[p]=='t'; return 1;
}
int px_statistics(char *text, int ident) {
    int r, s, d, a, p, i, t, value; float f;
    px_clear(); r=px_reply(text,"statisticRead",ident);
    s=px_key(r,"statistic"); if (s<0 || px_type[s]!='{') return 0;
    d=px_key(s,"dev");
    if (px_number(px_key(px_key(d,"temp"),"current"),&f)) { px_temp=f; px_temp_valid=1; }
    a=px_key(d,"bankVolt");
    for (i=0;i<px_banks;i++) {
        value=px_integer(px_at(a,i),2147483647);
        if (value>=0) { px_volts[i]=(float)(value/1000.0); px_bank_valid[i]=1; }
    }
    p=px_key(s,"pixPwrOuts");
    if (px_power) for (i=0;i<px_ports;i++) {
        t=px_at(px_key(p,"fuseGood"),i);
        if (t>=0 && (px_type[t]=='t' || px_type[t]=='f')) px_good[i]=px_type[t]=='t';
        t=px_at(px_key(p,"stat"),i);
        if (t>=0 && px_type[t]=='"') {
            if (px_equal(t,"Good")) px_state[i]=0;
            if (px_equal(t,"Inactv")) px_state[i]=1;
            if (px_equal(t,"OvrCur")) px_state[i]=2;
            if (px_equal(t,"FuseBlwn")) px_state[i]=3;
        }
    }
    return 1;
}
