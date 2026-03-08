use anyhow::Result;
use one_click_kb_switch::config::AppPaths;
use one_click_kb_switch::platform::build_backend;
use one_click_kb_switch::state::AppService;
use one_click_kb_switch::ui;

fn main() -> Result<()> {
    let paths = AppPaths::detect()?;
    let service = AppService::new(build_backend());
    let model = service.bootstrap(paths)?;
    service.persist(&model)?;
    ui::run(service, model)
}
