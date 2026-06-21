package main

import (
	"fmt"
	"strconv"

	"github.com/navidrome/navidrome/plugins/pdk/go/host"
	"github.com/navidrome/navidrome/plugins/pdk/go/lifecycle"
	"github.com/navidrome/navidrome/plugins/pdk/go/pdk"
	"github.com/navidrome/navidrome/plugins/pdk/go/scheduler"
)

const (
	syncTask   = "sync-task"
	syncCron   = "sync-cron"
)

type spotifySyncPlugin struct{}

func (s *spotifySyncPlugin) OnCallback(req scheduler.SchedulerCallbackRequest) error {
	pdk.Log(pdk.LogInfo, "Disparando sincronização de playlists do Spotify...")
	
	sidecarUrl, ok := pdk.GetConfig("sidecarUrl")
	if !ok || sidecarUrl == "" {
		sidecarUrl = "http://172.17.0.1:8090" // IP do gateway Docker por padrão
	}

	pdk.Log(pdk.LogInfo, fmt.Sprintf("Enviando requisição de sincronização ao sidecar em: %s/sync", sidecarUrl))
	
	resp, err := host.HTTPSend(host.HTTPRequest{
		Method: "POST",
		URL:    fmt.Sprintf("%s/sync", sidecarUrl),
		Headers: map[string]string{
			"Content-Type": "application/json",
		},
		TimeoutMs: 300000, // 5 minutos de timeout
	})
	
	if err != nil {
		pdk.Log(pdk.LogError, fmt.Sprintf("Falha ao se comunicar com o sidecar: %v", err))
		return err
	}
	
	pdk.Log(pdk.LogInfo, fmt.Sprintf("Sincronização concluída pelo sidecar (Status %d): %s", resp.StatusCode, string(resp.Body)))
	return nil
}

func (s *spotifySyncPlugin) OnInit() error {
	schedule, ok := pdk.GetConfig("schedule")
	if !ok {
		schedule = "2" // 2 da manhã padrão
	}

	schedInt, err := strconv.Atoi(schedule)
	if err != nil {
		return fmt.Errorf("Configuração de hora inválida %s: %v", schedule, err)
	}

	if schedInt < 0 || schedInt > 23 {
		return fmt.Errorf("Configuração de hora deve ser entre 0 e 23: %d", schedInt)
	}

	// Agendar sincronização diária na hora escolhida pela UI do Navidrome
	_, err = host.SchedulerScheduleRecurring(fmt.Sprintf("0 %d * * *", schedInt), syncCron, syncCron)
	if err != nil {
		return fmt.Errorf("Falha ao agendar tarefa recorrente de sincronização: %v", err)
	}

	checkOnStartup, ok := pdk.GetConfig("checkOnStartup")
	if !ok || checkOnStartup != "false" {
		// Agenda uma sincronização única 5 segundos após a inicialização do Navidrome
		_, err := host.SchedulerScheduleOneTime(5, syncTask, syncTask)
		if err != nil {
			pdk.Log(pdk.LogWarn, fmt.Sprintf("Falha ao agendar sincronização de inicialização: %v", err))
		}
	}

	pdk.Log(pdk.LogInfo, "Plugin Spotify Sync inicializado com sucesso!")
	return nil
}

func main() {}

func init() {
	lifecycle.Register(&spotifySyncPlugin{})
	scheduler.Register(&spotifySyncPlugin{})
}
