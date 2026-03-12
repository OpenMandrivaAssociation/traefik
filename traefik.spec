%undefine _debugsource_packages

Name:		traefik
Version:	3.6.10
Release:	1
Source0:	https://github.com/traefik/traefik/releases/download/v%{version}/traefik-v%{version}.src.tar.gz
Source1:	vendor.tar.xz
Source2:	traefik.yml
Source3:	traefik.logrotate
Summary:	The Traefik application proxy
URL:		https://doc.traefik.io/traefik
License:	MIT
Group:		Servers
BuildRequires:	golang

%patchlist
traefik-3.6.8-fix-bogus-deps.patch

%description
Traefik (pronounced traffic) is a modern HTTP reverse proxy and load balancer
that makes deploying microservices easy. Traefik integrates with your existing
infrastructure components (Docker, Swarm mode, Kubernetes, Consul, Etcd,
Rancher v2, Amazon ECS, ...) and configures itself automatically and
dynamically.

Pointing Traefik at your orchestrator should be the only configuration step
you need.

%prep
%autosetup -p1 -c -n %{name}-%{version} -a1

%conf
go generate

%build
CGO_ENABLED=1 go build \
	-mod=vendor \
	-ldflags "-X github.com/traefik/traefik/v3/pkg/version.Version=%{version} \
		-X github.com/traefik/traefik/v3/pkg/version.Codename='' \
		-X github.com/traefik/traefik/v3/pkg/version.BuildDate=${build_date}" \
	-o traefik \
	./cmd/traefik

%install
mkdir -p %{buildroot}%{_bindir} \
	%{buildroot}%{_sysusersdir} \
	%{buildroot}%{_unitdir} \
	%{buildroot}%{_sysconfdir}/traefik \
	%{buildroot}/srv/traefik \
	%{buildroot}/var/log/traefik

cat >%{buildroot}%{_sysusersdir}/%{name}.conf <<EOF
u	traefik	-	"HTTP reverse proxy and load balancer"	/srv/traefik	-
m	traefik	traefik
EOF

cat >%{buildroot}%{_unitdir}/%{name}.service <<'EOF'
[Unit]
Description=Traefik
Documentation=https://doc.traefik.io/traefik/
After=network.target network-online.target
Requires=network-online.target
AssertFileIsExecutable=%{_bindir}/traefik
AssertPathExists=%{_sysconfdir}/traefik/traefik.yml

[Service]
Type=notify
EnvironmentFile=-%{_sysconfdir}/sysconfig/traefik
ExecStart=%{_bindir}/traefik --configFile=%{_sysconfdir}/traefik/traefik.yml
ExecReload=kill -HUP $MAINPID ; kill -USR1 $MAINPID
User=traefik
WorkingDirectory=~
Restart=always
WatchdogSec=1s
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_BIND_SERVICE
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

install -c -m 755 traefik %{buildroot}%{_bindir}
install -c -m 644 %{S:2} %{buildroot}%{_sysconfdir}/traefik/

# acme storage
touch %{buildroot}/srv/traefik/acme.json

# logging
mkdir -p %{buildroot}%{_localstatedir}/log/%{name}

mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
install -m 644 %{S:3} %{buildroot}/%{_sysconfdir}/logrotate.d/traefik

mkdir -p %{buildroot}%{_sysconfdir}/sysconfig/
cat >%{buildroot}%{_sysconfdir}/sysconfig/traefik <<EOF
# PowerDNS API Configuration for Traefik ACME DNS-01 Challenge
#PDNS_API_URL=http://127.0.0.1:8081
# Keep in sync with api-key= in /etc/powerdns/pdns.conf
#PDNS_API_KEY=your_api_key_here

# Optional: Time in seconds to wait for DNS propagation before
# Traefik checks it
PDNS_PROPAGATION_DELAY=30
EOF

%files
%{_bindir}/traefik
%{_sysusersdir}/%{name}.conf
%{_unitdir}/%{name}.service
%dir %{_sysconfdir}/traefik
%config(noreplace) %{_sysconfdir}/traefik/traefik.yml
%config(noreplace) %{_sysconfdir}/logrotate.d/traefik
%config(noreplace) %verify(not md5 size mtime) %attr(600,traefik,traefik) /srv/traefik/acme.json
%config(noreplace) %verify(not md5 size mtime) %{_sysconfdir}/sysconfig/traefik
%dir %attr(755,traefik,traefik) /srv/traefik
%dir /var/log/traefik
