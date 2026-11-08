# Mobile shell and Home Screen helpers

App imports usePhoneLayout, MobileNavigation, MobileConnection, HomeScreenHelp and registerHomeScreenWorker from this folder. Shared map/panel modules keep their existing public interfaces and APIs. The layout switches at900px, hides phone messaging controls through scoped CSS, and retains desktop navigation above that width.

Phone mutation defaults use networkMode always with retry=false so an attempted offline operation fails visibly rather than resuming silently when connectivity returns. Query/SSE behavior is unchanged. Production worker registration requires a secure context; see docs/MOBILE.md for deployment and test details.
