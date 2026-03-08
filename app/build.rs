fn main() {
    #[cfg(target_os = "windows")]
    {
        let mut resource = winres::WindowsResource::new();
        resource.set_icon("assets/app.ico");
        resource.set_manifest_file("windows/app.manifest");
        resource.set("FileDescription", "One Click KB Switch");
        resource.set("ProductName", "One Click KB Switch");
        resource.set("LegalCopyright", "Copyright (c) 2026 Mykola");
        resource
            .compile()
            .expect("failed to compile Windows resources");
    }
}
